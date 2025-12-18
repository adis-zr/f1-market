"""Tests for wallet service."""
import pytest
from decimal import Decimal
from db import db
from db.models import TransactionType
from services.wallet_service import WalletService, InsufficientBalanceError


class TestGetOrCreateWallet:
    """Tests for get_or_create_wallet method."""

    def test_create_wallet_for_new_user(self, app, test_user):
        """Test creating a new wallet for a user."""
        with app.app_context():
            wallet = WalletService.get_or_create_wallet(test_user.id)

            assert wallet is not None
            assert wallet.user_id == test_user.id
            assert wallet.balance == Decimal('0')
            assert wallet.locked_balance == Decimal('0')

    def test_get_existing_wallet(self, app, test_wallet, test_user):
        """Test getting an existing wallet."""
        with app.app_context():
            wallet = WalletService.get_or_create_wallet(test_user.id)

            assert wallet is not None
            assert wallet.user_id == test_user.id
            # Should have balance from test_wallet fixture
            assert wallet.balance == Decimal('1000.0')

    def test_get_wallet_with_for_update_lock(self, app, test_user):
        """Test getting wallet with FOR UPDATE lock."""
        with app.app_context():
            wallet = WalletService.get_or_create_wallet(test_user.id, for_update=True)

            assert wallet is not None
            assert wallet.user_id == test_user.id


class TestBalanceOperations:
    """Tests for balance retrieval methods."""

    def test_get_balance_with_no_locked(self, app, test_wallet, test_user):
        """Test getting balance when nothing is locked."""
        with app.app_context():
            balance = WalletService.get_balance(test_user.id)

            assert balance == Decimal('1000.0')

    def test_get_balance_with_locked_balance(self, app, test_wallet, test_user):
        """Test getting available balance when some is locked."""
        with app.app_context():
            # Lock some balance
            WalletService.lock_balance(test_user.id, Decimal('300.0'))
            db.session.commit()

            balance = WalletService.get_balance(test_user.id)

            assert balance == Decimal('700.0')

    def test_get_total_balance(self, app, test_wallet, test_user):
        """Test getting total balance."""
        with app.app_context():
            total = WalletService.get_total_balance(test_user.id)

            assert total == Decimal('1000.0')

    def test_get_locked_balance(self, app, test_wallet, test_user):
        """Test getting locked balance."""
        with app.app_context():
            # Lock some balance
            WalletService.lock_balance(test_user.id, Decimal('250.0'))
            db.session.commit()

            locked = WalletService.get_locked_balance(test_user.id)

            assert locked == Decimal('250.0')


class TestLockBalance:
    """Tests for lock_balance method."""

    def test_lock_balance_success(self, app, test_wallet, test_user):
        """Test successfully locking balance."""
        with app.app_context():
            result = WalletService.lock_balance(test_user.id, Decimal('500.0'))
            db.session.commit()

            assert result is True
            assert WalletService.get_locked_balance(test_user.id) == Decimal('500.0')
            assert WalletService.get_balance(test_user.id) == Decimal('500.0')

    def test_lock_balance_insufficient_funds(self, app, test_wallet, test_user):
        """Test locking more than available balance."""
        with app.app_context():
            with pytest.raises(InsufficientBalanceError):
                WalletService.lock_balance(test_user.id, Decimal('2000.0'))

    def test_lock_balance_zero_amount_raises(self, app, test_wallet, test_user):
        """Test that locking zero amount raises ValueError."""
        with app.app_context():
            with pytest.raises(ValueError, match="Amount must be positive"):
                WalletService.lock_balance(test_user.id, Decimal('0'))

    def test_lock_balance_negative_amount_raises(self, app, test_wallet, test_user):
        """Test that locking negative amount raises ValueError."""
        with app.app_context():
            with pytest.raises(ValueError, match="Amount must be positive"):
                WalletService.lock_balance(test_user.id, Decimal('-100.0'))


class TestUnlockBalance:
    """Tests for unlock_balance method."""

    def test_unlock_balance_success(self, app, test_wallet, test_user):
        """Test successfully unlocking balance."""
        with app.app_context():
            # First lock some balance
            WalletService.lock_balance(test_user.id, Decimal('500.0'))
            db.session.commit()

            # Then unlock some
            result = WalletService.unlock_balance(test_user.id, Decimal('200.0'))
            db.session.commit()

            assert result is True
            assert WalletService.get_locked_balance(test_user.id) == Decimal('300.0')

    def test_unlock_balance_more_than_locked(self, app, test_wallet, test_user):
        """Test unlocking more than locked amount sets locked to 0."""
        with app.app_context():
            # Lock some balance
            WalletService.lock_balance(test_user.id, Decimal('100.0'))
            db.session.commit()

            # Try to unlock more than locked
            result = WalletService.unlock_balance(test_user.id, Decimal('500.0'))
            db.session.commit()

            assert result is True
            # Should be 0, not negative
            assert WalletService.get_locked_balance(test_user.id) == Decimal('0')


class TestLedgerOperations:
    """Tests for ledger operations."""

    def test_add_ledger_entry_credit(self, app, test_user):
        """Test adding a credit ledger entry."""
        with app.app_context():
            entry = WalletService.add_ledger_entry(
                test_user.id,
                Decimal('500.0'),
                TransactionType.DEPOSIT,
                description='Test credit'
            )
            db.session.commit()

            assert entry is not None
            assert entry.amount == Decimal('500.0')
            assert entry.transaction_type == TransactionType.DEPOSIT
            assert WalletService.get_balance(test_user.id) == Decimal('500.0')

    def test_add_ledger_entry_debit(self, app, test_wallet, test_user):
        """Test adding a debit ledger entry."""
        with app.app_context():
            entry = WalletService.add_ledger_entry(
                test_user.id,
                Decimal('-200.0'),
                TransactionType.BUY,
                reference_type='market',
                reference_id=1,
                description='Test debit'
            )
            db.session.commit()

            assert entry is not None
            assert entry.amount == Decimal('-200.0')
            assert WalletService.get_balance(test_user.id) == Decimal('800.0')

    def test_add_ledger_entry_insufficient_balance(self, app, test_user):
        """Test that debit fails when balance is insufficient."""
        with app.app_context():
            # First create wallet with 0 balance
            WalletService.get_or_create_wallet(test_user.id)

            with pytest.raises(InsufficientBalanceError):
                WalletService.add_ledger_entry(
                    test_user.id,
                    Decimal('-100.0'),
                    TransactionType.BUY,
                    description='Test debit should fail'
                )

    def test_get_ledger_history(self, app, test_wallet, test_user):
        """Test getting ledger history."""
        with app.app_context():
            # Add some more entries
            WalletService.add_ledger_entry(
                test_user.id,
                Decimal('100.0'),
                TransactionType.DEPOSIT,
                description='Second deposit'
            )
            WalletService.add_ledger_entry(
                test_user.id,
                Decimal('-50.0'),
                TransactionType.BUY,
                description='Buy shares'
            )
            db.session.commit()

            history = WalletService.get_ledger_history(test_user.id)

            # Should have 3 entries (1 from fixture, 2 added)
            assert len(history) == 3
            # Most recent first
            assert history[0].amount == Decimal('-50.0')
            assert history[1].amount == Decimal('100.0')

    def test_get_ledger_history_with_limit(self, app, test_wallet, test_user):
        """Test getting ledger history with limit."""
        with app.app_context():
            # Add more entries
            for i in range(5):
                WalletService.add_ledger_entry(
                    test_user.id,
                    Decimal('10.0'),
                    TransactionType.DEPOSIT,
                    description=f'Deposit {i}'
                )
            db.session.commit()

            history = WalletService.get_ledger_history(test_user.id, limit=3)

            assert len(history) == 3
