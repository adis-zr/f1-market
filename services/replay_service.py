"""Replay service for managing replay sessions and operations."""
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional
from sqlalchemy import func, desc

from db import db, utc_now, MarketStatus, TransactionType, User
from db.replay_models import (
    ReplaySession, ReplaySessionStatus, ReplayWallet, ReplayMarket,
    ReplayPosition, ReplayTrade, ReplayLedgerEntry, ReplayPriceHistory,
    ReplayDifficulty, ReplayDriverPosition, ReplayAIPlayer, ReplayScheduledAITrade
)
from data.f1_2024 import DRIVERS_2024, RACES_2024, get_race_info, get_points_for_position
from pricing.bonding_curve import price, buy_cost, sell_payout
from services.replay_ai_service import ReplayAIService


# Constants
INITIAL_BALANCE = Decimal('100')
BONDING_A = Decimal('0.1')  # Bonding curve slope
BONDING_B = Decimal('0.5')  # Bonding curve baseline
TOTAL_RACES = 24
DEFAULT_MARKET_DURATION = 10  # seconds


class ReplaySessionNotFoundError(Exception):
    """Raised when replay session is not found."""
    pass


class ReplayMarketClosedError(Exception):
    """Raised when trying to trade on a closed replay market."""
    pass


class ReplayInsufficientBalanceError(Exception):
    """Raised when user doesn't have enough replay balance."""
    pass


class ReplayInsufficientSharesError(Exception):
    """Raised when user doesn't have enough shares to sell."""
    pass


class ReplayMarketWindowClosedError(Exception):
    """Raised when trying to trade after the market window has closed."""
    pass


class ReplayService:
    """Service for managing replay sessions."""

    @staticmethod
    def start_replay(user_id: int, difficulty: ReplayDifficulty = ReplayDifficulty.MEDIUM) -> Dict:
        """Start a new replay session for a user.

        Creates a new ReplaySession, ReplayWallet with $100 starting balance,
        and an initial ledger entry.

        Args:
            user_id: User ID
            difficulty: Difficulty level (easy, medium, hard)

        Returns:
            Dict with session details
        """
        try:
            # Create new replay session
            session = ReplaySession(
                user_id=user_id,
                current_race=0,  # Not started yet
                status=ReplaySessionStatus.ACTIVE,
                difficulty=difficulty,
                started_at=utc_now()
            )
            db.session.add(session)
            db.session.flush()  # Get session ID

            # Create wallet with initial balance
            wallet = ReplayWallet(
                session_id=session.id,
                balance=INITIAL_BALANCE,
                locked_balance=Decimal('0')
            )
            db.session.add(wallet)

            # Create initial ledger entry (deposit)
            ledger_entry = ReplayLedgerEntry(
                session_id=session.id,
                amount=INITIAL_BALANCE,
                transaction_type=TransactionType.DEPOSIT,
                description="Initial replay balance"
            )
            db.session.add(ledger_entry)

            db.session.commit()

            return ReplayService.get_session_state(session.id)

        except Exception as e:
            db.session.rollback()
            raise

    @staticmethod
    def get_active_session(user_id: int) -> Optional[ReplaySession]:
        """Get user's active replay session, if any.

        Args:
            user_id: User ID

        Returns:
            ReplaySession or None
        """
        return ReplaySession.query.filter_by(
            user_id=user_id,
            status=ReplaySessionStatus.ACTIVE
        ).first()

    @staticmethod
    def get_session_state(session_id: int, execute_ai_trades: bool = True) -> Dict:
        """Get complete state of a replay session.

        Args:
            session_id: Session ID
            execute_ai_trades: Whether to execute pending AI trades (lazy execution)

        Returns:
            Dict with full session state

        Raises:
            ReplaySessionNotFoundError: If session not found
        """
        session = db.session.get(ReplaySession, session_id)
        if not session:
            raise ReplaySessionNotFoundError(f"Session {session_id} not found")

        # Execute pending AI trades if within window (lazy execution)
        if execute_ai_trades and session.market_opens_at:
            ReplayAIService.execute_pending_ai_trades(session_id, utc_now())

        wallet = session.wallet

        # Calculate market timing info
        market_timing = ReplayService._get_market_timing(session)

        # Get current race info
        current_race_info = None
        if session.current_race > 0:
            race_data = get_race_info(session.current_race)
            if race_data:
                current_race_info = {
                    "race_number": session.current_race,
                    "name": race_data["name"],
                    "venue": race_data["venue"],
                    "date": race_data["date"],
                    "status": "current" if session.status == ReplaySessionStatus.ACTIVE else "completed"
                }

        # Get current race markets
        markets = []
        if session.current_race > 0:
            market_records = ReplayMarket.query.filter_by(
                session_id=session_id,
                race_number=session.current_race
            ).order_by(ReplayMarket.driver_code).all()

            for market in market_records:
                supply = ReplayService._get_market_supply(market.id)
                current_price = price(supply, Decimal(str(market.a)), Decimal(str(market.b)))
                markets.append({
                    "market_id": market.id,
                    "race_number": market.race_number,
                    "driver_code": market.driver_code,
                    "driver_name": market.driver_name,
                    "team_name": market.team_name,
                    "status": market.status.value,
                    "current_price": float(current_price),
                    "current_supply": float(supply),
                    "settlement_price": float(market.settlement_price) if market.settlement_price else None,
                    "payout_per_share": float(market.payout_per_share) if market.payout_per_share else None
                })

        # Get all positions with non-zero shares
        positions = []
        position_records = ReplayPosition.query.filter(
            ReplayPosition.session_id == session_id,
            ReplayPosition.shares > 0
        ).all()

        for pos in position_records:
            market = db.session.get(ReplayMarket, pos.market_id)
            if market:
                shares = Decimal(str(pos.shares))
                avg_entry = Decimal(str(pos.avg_entry_price))
                is_settled = market.status == MarketStatus.SETTLED

                if is_settled:
                    # For settled markets, use the fixed settlement price
                    current_price = Decimal(str(market.settlement_price)) if market.settlement_price else Decimal('0')
                    market_value = shares * current_price
                else:
                    # For open markets, use bonding curve price
                    supply = ReplayService._get_market_supply(market.id)
                    current_price = price(supply, Decimal(str(market.a)), Decimal(str(market.b)))
                    market_value = shares * current_price

                unrealized_pnl = (current_price - avg_entry) * shares

                # Can sell if: settled market OR current race's open market
                can_sell = is_settled or (market.status == MarketStatus.OPEN and market.race_number == session.current_race)

                positions.append({
                    "position_id": pos.id,
                    "market_id": pos.market_id,
                    "driver_code": market.driver_code,
                    "driver_name": market.driver_name,
                    "race_number": market.race_number,
                    "shares": float(pos.shares),
                    "avg_entry_price": float(pos.avg_entry_price),
                    "current_price": float(current_price),
                    "market_value": float(market_value),
                    "unrealized_pnl": float(unrealized_pnl),
                    "realized_pnl": float(pos.realized_pnl),
                    "is_settled": is_settled,
                    "can_sell": can_sell
                })

        # Calculate total P&L
        total_realized_pnl = sum(p["realized_pnl"] for p in positions)
        total_unrealized_pnl = sum(p["unrealized_pnl"] for p in positions)

        # Get all races info
        all_races = []
        for race_num in range(1, TOTAL_RACES + 1):
            race_data = get_race_info(race_num)
            if race_data:
                if race_num < session.current_race:
                    status = "completed"
                elif race_num == session.current_race:
                    status = "current"
                else:
                    status = "upcoming"

                all_races.append({
                    "race_number": race_num,
                    "name": race_data["name"],
                    "venue": race_data["venue"],
                    "date": race_data["date"],
                    "status": status
                })

        return {
            "session": {
                "session_id": session.id,
                "user_id": session.user_id,
                "current_race": session.current_race,
                "status": session.status.value,
                "difficulty": session.difficulty.value,
                "started_at": session.started_at.isoformat() if session.started_at else None,
                "completed_at": session.completed_at.isoformat() if session.completed_at else None,
                "final_balance": float(session.final_balance) if session.final_balance else None
            },
            "wallet": {
                "balance": float(wallet.balance) if wallet else 0,
                "locked_balance": float(wallet.locked_balance) if wallet else 0
            },
            "current_race_info": current_race_info,
            "markets": markets,
            "positions": positions,
            "total_pnl": {
                "realized": total_realized_pnl,
                "unrealized": total_unrealized_pnl,
                "total": total_realized_pnl + total_unrealized_pnl
            },
            "all_races": all_races,
            "market_timing": market_timing
        }

    @staticmethod
    def advance_to_next_race(session_id: int) -> Dict:
        """Advance to the next race.

        If current_race > 0, settles the current race first using historical results.
        Then increments current_race and creates markets for the new race.
        If current_race > 24, marks session as COMPLETED.

        Args:
            session_id: Session ID

        Returns:
            Dict with settlement summary (if applicable) and new session state

        Raises:
            ReplaySessionNotFoundError: If session not found
        """
        try:
            session = ReplaySession.query.filter_by(id=session_id).with_for_update().first()
            if not session:
                raise ReplaySessionNotFoundError(f"Session {session_id} not found")

            if session.status != ReplaySessionStatus.ACTIVE:
                raise ValueError(f"Session is not active (status: {session.status.value})")

            settlement_summary = None

            # Ensure AI players exist before settling (in case session predates AI feature)
            ReplayAIService.ensure_ai_players_exist()

            # If we have a current race, settle it first
            if session.current_race > 0:
                settlement_summary = ReplayService._settle_race(session, session.current_race)

            # Advance to next race
            session.current_race += 1

            if session.current_race <= TOTAL_RACES:
                # Create markets for new race
                ReplayService._create_race_markets(session, session.current_race)
            else:
                # Season complete
                session.status = ReplaySessionStatus.COMPLETED
                session.completed_at = utc_now()
                # Cache final balance for leaderboard
                wallet = session.wallet
                if wallet:
                    session.final_balance = wallet.balance

            db.session.commit()

            return {
                "settlement_summary": settlement_summary,
                "new_state": ReplayService.get_session_state(session_id)
            }

        except Exception as e:
            db.session.rollback()
            raise

    @staticmethod
    def _settle_race(session: ReplaySession, race_number: int) -> Dict:
        """Settle all markets for a race using historical results.

        Args:
            session: ReplaySession object
            race_number: Race number to settle

        Returns:
            Dict with settlement summary
        """
        race_data = get_race_info(race_number)
        if not race_data:
            raise ValueError(f"Race {race_number} data not found")

        # Build results lookup: driver_code -> position
        results_lookup = {code: pos for code, pos in race_data["results"]}

        # Get all markets for this race
        markets = ReplayMarket.query.filter_by(
            session_id=session.id,
            race_number=race_number,
            status=MarketStatus.OPEN
        ).with_for_update().all()

        settlement_results = []
        user_settled_positions = []
        total_settled_value = Decimal('0')

        for market in markets:
            driver_code = market.driver_code
            position = results_lookup.get(driver_code, 0)  # 0 = DNF

            # Get points for position
            points = get_points_for_position(position)

            # Settlement price = points earned
            market.settlement_price = points

            # Payout per share = points (simple 1:1 for now)
            payout_per_share = points
            market.payout_per_share = payout_per_share
            market.status = MarketStatus.SETTLED

            settlement_results.append({
                "driver_code": driver_code,
                "driver_name": market.driver_name,
                "position": position,
                "points": float(points),
                "payout_per_share": float(payout_per_share)
            })

            # Check if user has position (for display purposes only - NO auto-payout)
            position_record = ReplayPosition.query.filter(
                ReplayPosition.session_id == session.id,
                ReplayPosition.market_id == market.id,
                ReplayPosition.shares > 0
            ).first()

            if position_record:
                shares = Decimal(str(position_record.shares))
                settlement_value = shares * payout_per_share
                user_settled_positions.append({
                    "driver_code": driver_code,
                    "shares": float(shares),
                    "settlement_value": float(settlement_value),
                    "points_per_share": float(payout_per_share)
                })
                total_settled_value += settlement_value
                # Note: Shares remain unchanged for carry-forward
                # User must explicitly sell to convert to cash

        # Build mini-leaderboard comparing user to AI agents
        wallet = ReplayWallet.query.filter_by(session_id=session.id).first()
        user_cash = float(wallet.balance) if wallet else 0

        # Calculate user's total portfolio value (cash + all position market values)
        all_positions = ReplayPosition.query.filter(
            ReplayPosition.session_id == session.id,
            ReplayPosition.shares > 0
        ).all()

        user_positions_value = Decimal('0')
        for pos in all_positions:
            market = db.session.get(ReplayMarket, pos.market_id)
            if market:
                shares = Decimal(str(pos.shares))
                if market.status == MarketStatus.SETTLED:
                    pos_value = shares * Decimal(str(market.settlement_price or 0))
                else:
                    supply = ReplayService._get_market_supply(market.id)
                    current_price = price(supply, Decimal(str(market.a)), Decimal(str(market.b)))
                    pos_value = shares * current_price
                user_positions_value += pos_value

        user_balance = user_cash + float(user_positions_value)

        # Get AI standings at this race
        ai_standings = ReplayAIService.get_ai_standings_at_race(
            session.difficulty,
            race_number
        )

        # Merge user with AI standings
        all_standings = ai_standings + [{
            "name": "You",
            "balance": round(user_balance, 2),
            "is_ai": False
        }]
        all_standings.sort(key=lambda x: x["balance"], reverse=True)

        # Assign ranks
        for i, entry in enumerate(all_standings, 1):
            entry["rank"] = i

        # Find user's position
        user_entry = next(e for e in all_standings if not e["is_ai"])
        user_rank = user_entry["rank"]

        # Include all players in mini-leaderboard
        mini_leaderboard = {
            "user_rank": user_rank,
            "user_balance": round(user_balance, 2),
            "total_players": len(all_standings),
            "entries": all_standings
        }

        return {
            "race_number": race_number,
            "race_name": race_data["name"],
            "results": settlement_results,
            "your_settled_positions": user_settled_positions,
            "total_settled_value": float(total_settled_value),
            "mini_leaderboard": mini_leaderboard
        }

    @staticmethod
    def _create_race_markets(session: ReplaySession, race_number: int) -> List[ReplayMarket]:
        """Create markets for all 20 drivers for a race.

        Carries forward existing positions from driver positions table.
        Sets up market timing and schedules AI trades.

        Args:
            session: ReplaySession object
            race_number: Race number

        Returns:
            List of created ReplayMarket objects
        """
        markets = []

        # Set market timing
        session.market_opens_at = utc_now()

        # Get existing driver positions for carry-forward
        driver_positions = {
            dp.driver_code: dp
            for dp in ReplayDriverPosition.query.filter_by(
                session_id=session.id
            ).all()
        }

        for driver in DRIVERS_2024:
            market = ReplayMarket(
                session_id=session.id,
                race_number=race_number,
                driver_code=driver["code"],
                driver_name=driver["name"],
                team_name=driver["team"],
                status=MarketStatus.OPEN,
                a=BONDING_A,
                b=BONDING_B
            )
            db.session.add(market)
            markets.append(market)

        db.session.flush()  # Get IDs

        # Create initial price history entries and carry forward positions
        for market in markets:
            driver_pos = driver_positions.get(market.driver_code)
            initial_supply = Decimal('0')

            if driver_pos and driver_pos.shares > 0:
                initial_supply = driver_pos.shares

                # Create position record for this market with carried shares
                position = ReplayPosition(
                    session_id=session.id,
                    market_id=market.id,
                    shares=driver_pos.shares,
                    avg_entry_price=driver_pos.total_cost_basis / driver_pos.shares if driver_pos.shares > 0 else Decimal('0'),
                    realized_pnl=Decimal('0')
                )
                db.session.add(position)

            initial_price = price(initial_supply, BONDING_A, BONDING_B)
            price_history = ReplayPriceHistory(
                market_id=market.id,
                timestamp=utc_now(),
                price=initial_price,
                supply=initial_supply,
                reason="initial"
            )
            db.session.add(price_history)

        # Schedule AI trades for this race
        ReplayAIService.schedule_ai_trades_for_race(
            session_id=session.id,
            race_number=race_number,
            market_opens_at=session.market_opens_at,
            duration_seconds=session.market_duration_seconds,
            difficulty=session.difficulty
        )

        return markets

    @staticmethod
    def reset_replay(session_id: int, difficulty: Optional[ReplayDifficulty] = None) -> Dict:
        """Reset a replay session to start fresh.

        Deletes all trades, positions, ledger entries, markets, and scheduled AI trades.
        Resets wallet to $100 and current_race to 0.

        Args:
            session_id: Session ID
            difficulty: Optional new difficulty level

        Returns:
            Fresh session state
        """
        try:
            session = ReplaySession.query.filter_by(id=session_id).with_for_update().first()
            if not session:
                raise ReplaySessionNotFoundError(f"Session {session_id} not found")

            # Delete all related data (cascades handle most of this)
            ReplayPriceHistory.query.filter(
                ReplayPriceHistory.market_id.in_(
                    db.session.query(ReplayMarket.id).filter_by(session_id=session_id)
                )
            ).delete(synchronize_session=False)

            ReplayTrade.query.filter_by(session_id=session_id).delete(synchronize_session=False)
            ReplayPosition.query.filter_by(session_id=session_id).delete(synchronize_session=False)
            ReplayDriverPosition.query.filter_by(session_id=session_id).delete(synchronize_session=False)
            ReplayLedgerEntry.query.filter_by(session_id=session_id).delete(synchronize_session=False)
            ReplayScheduledAITrade.query.filter_by(session_id=session_id).delete(synchronize_session=False)
            ReplayMarket.query.filter_by(session_id=session_id).delete(synchronize_session=False)

            # Reset wallet
            wallet = session.wallet
            if wallet:
                wallet.balance = INITIAL_BALANCE
                wallet.locked_balance = Decimal('0')

            # Reset session
            session.current_race = 0
            session.status = ReplaySessionStatus.ACTIVE
            session.completed_at = None
            session.final_balance = None
            session.market_opens_at = None

            # Update difficulty if provided
            if difficulty is not None:
                session.difficulty = difficulty

            # Create new initial ledger entry
            ledger_entry = ReplayLedgerEntry(
                session_id=session.id,
                amount=INITIAL_BALANCE,
                transaction_type=TransactionType.DEPOSIT,
                description="Initial replay balance (reset)"
            )
            db.session.add(ledger_entry)

            db.session.commit()

            return ReplayService.get_session_state(session_id)

        except Exception as e:
            db.session.rollback()
            raise

    @staticmethod
    def get_leaderboard(
        limit: int = 50,
        user_id: Optional[int] = None,
        difficulty: Optional[ReplayDifficulty] = None
    ) -> Dict:
        """Get leaderboard of completed replay sessions.

        Args:
            limit: Maximum number of entries to return
            user_id: Optional user ID to include their best score
            difficulty: Optional difficulty filter

        Returns:
            Dict with leaderboard entries and user's best (if provided)
        """
        # Build query for human players
        entries_query = db.session.query(
            ReplaySession, User
        ).join(
            User, ReplaySession.user_id == User.id
        ).filter(
            ReplaySession.status == ReplaySessionStatus.COMPLETED,
            ReplaySession.final_balance.isnot(None)
        )

        if difficulty:
            entries_query = entries_query.filter(ReplaySession.difficulty == difficulty)

        entries_query = entries_query.order_by(
            desc(ReplaySession.final_balance)
        )

        human_entries = []
        for session, user in entries_query.all():
            final_balance = float(session.final_balance) if session.final_balance else 0
            human_entries.append({
                "username": user.username or user.email.split('@')[0],
                "user_id": user.id,
                "is_ai": False,
                "final_balance": final_balance,
                "return_pct": ((final_balance - 100) / 100) * 100,
                "difficulty": session.difficulty.value,
                "completed_at": session.completed_at.isoformat() if session.completed_at else None
            })

        # Get AI players for this difficulty
        ai_entries = []
        if difficulty:
            ai_players = ReplayAIPlayer.query.filter_by(difficulty=difficulty).all()
            for player in ai_players:
                final_balance = float(player.final_balance)
                ai_entries.append({
                    "username": player.name,
                    "user_id": None,
                    "is_ai": True,
                    "final_balance": final_balance,
                    "return_pct": ((final_balance - 100) / 100) * 100,
                    "difficulty": difficulty.value,
                    "completed_at": None
                })

        # Merge and sort all entries by final_balance
        all_entries = human_entries + ai_entries
        all_entries.sort(key=lambda x: x["final_balance"], reverse=True)

        # Assign ranks and limit
        entries = []
        for rank, entry in enumerate(all_entries[:limit], 1):
            entry["rank"] = rank
            entries.append(entry)

        # Get user's best if provided
        your_best = None
        if user_id:
            user_best_query = ReplaySession.query.filter_by(
                user_id=user_id,
                status=ReplaySessionStatus.COMPLETED
            ).filter(
                ReplaySession.final_balance.isnot(None)
            )

            if difficulty:
                user_best_query = user_best_query.filter(ReplaySession.difficulty == difficulty)

            user_best_session = user_best_query.order_by(
                desc(ReplaySession.final_balance)
            ).first()

            if user_best_session:
                # Count entries with higher balance (including AI)
                final_balance = float(user_best_session.final_balance)
                higher_count = sum(1 for e in all_entries if e["final_balance"] > final_balance)

                your_best = {
                    "rank": higher_count + 1,
                    "final_balance": final_balance,
                    "return_pct": ((final_balance - 100) / 100) * 100,
                    "difficulty": user_best_session.difficulty.value,
                    "completed_at": user_best_session.completed_at.isoformat() if user_best_session.completed_at else None
                }

        return {
            "entries": entries,
            "your_best": your_best
        }

    @staticmethod
    def _get_market_supply(market_id: int) -> Decimal:
        """Get current supply for a replay market.

        Args:
            market_id: ReplayMarket ID

        Returns:
            Current supply as Decimal
        """
        result = db.session.query(func.sum(ReplayPosition.shares)).filter(
            ReplayPosition.market_id == market_id
        ).scalar()

        if result is None:
            return Decimal('0')

        return Decimal(str(result))

    @staticmethod
    def _get_market_timing(session: ReplaySession) -> Dict:
        """Get market timing info for a session.

        Args:
            session: ReplaySession object

        Returns:
            Dict with timing info
        """
        now = utc_now()

        if not session.market_opens_at or session.current_race == 0:
            return {
                "opens_at": None,
                "duration_seconds": session.market_duration_seconds,
                "server_time": now.isoformat(),
                "time_remaining": 0,
                "can_trade": False,
                "market_phase": "pending"
            }

        opens_at = session.market_opens_at
        duration = session.market_duration_seconds

        # Ensure timezone compatibility - make opens_at timezone-aware if needed
        if opens_at.tzinfo is None:
            from datetime import timezone
            opens_at = opens_at.replace(tzinfo=timezone.utc)

        closes_at = opens_at + timedelta(seconds=duration)

        time_remaining = max(0, (closes_at - now).total_seconds())
        can_trade = time_remaining > 0

        # Determine market phase
        if now < opens_at:
            market_phase = "pending"
        elif can_trade:
            market_phase = "open"
        else:
            market_phase = "closed"

        return {
            "opens_at": opens_at.isoformat(),
            "closes_at": closes_at.isoformat(),
            "duration_seconds": duration,
            "server_time": now.isoformat(),
            "time_remaining": round(time_remaining, 1),
            "can_trade": can_trade,
            "market_phase": market_phase
        }

    @staticmethod
    def is_within_trading_window(session: ReplaySession) -> bool:
        """Check if the current market window is open for trading.

        Args:
            session: ReplaySession object

        Returns:
            True if trading is allowed, False otherwise
        """
        if not session.market_opens_at or session.current_race == 0:
            return False

        opens_at = session.market_opens_at
        # Ensure timezone compatibility
        if opens_at.tzinfo is None:
            from datetime import timezone
            opens_at = opens_at.replace(tzinfo=timezone.utc)

        now = utc_now()
        closes_at = opens_at + timedelta(seconds=session.market_duration_seconds)

        return now < closes_at

    @staticmethod
    def settle_current_race(session_id: int) -> Dict:
        """Settle the current race when the market window closes.

        Executes all remaining AI trades and settles the race.
        Called by frontend when timer expires.

        Args:
            session_id: Session ID

        Returns:
            Dict with settlement summary and new state

        Raises:
            ReplaySessionNotFoundError: If session not found
            ReplayMarketWindowClosedError: If trying to settle while window is still open
        """
        try:
            session = ReplaySession.query.filter_by(id=session_id).with_for_update().first()
            if not session:
                raise ReplaySessionNotFoundError(f"Session {session_id} not found")

            if session.status != ReplaySessionStatus.ACTIVE:
                raise ValueError(f"Session is not active (status: {session.status.value})")

            if session.current_race == 0:
                raise ValueError("No race in progress to settle")

            # Check if window is still open (with 0.5s grace period)
            if session.market_opens_at:
                opens_at = session.market_opens_at
                # Ensure timezone compatibility
                if opens_at.tzinfo is None:
                    from datetime import timezone
                    opens_at = opens_at.replace(tzinfo=timezone.utc)
                closes_at = opens_at + timedelta(seconds=session.market_duration_seconds)
                now = utc_now()
                if now < closes_at - timedelta(seconds=0.5):
                    raise ReplayMarketWindowClosedError(
                        f"Trading window still open for {(closes_at - now).total_seconds():.1f}s"
                    )

            # Execute all remaining AI trades
            far_future = utc_now() + timedelta(hours=24)
            ReplayAIService.execute_pending_ai_trades(session_id, far_future)

            # Ensure AI players exist
            ReplayAIService.ensure_ai_players_exist()

            # Settle the current race
            settlement_summary = ReplayService._settle_race(session, session.current_race)

            # Advance to next race
            session.current_race += 1

            if session.current_race <= TOTAL_RACES:
                # Create markets for new race
                ReplayService._create_race_markets(session, session.current_race)
            else:
                # Season complete
                session.status = ReplaySessionStatus.COMPLETED
                session.completed_at = utc_now()
                wallet = session.wallet
                if wallet:
                    session.final_balance = wallet.balance

            db.session.commit()

            return {
                "settlement_summary": settlement_summary,
                "new_state": ReplayService.get_session_state(session_id)
            }

        except Exception as e:
            db.session.rollback()
            raise
