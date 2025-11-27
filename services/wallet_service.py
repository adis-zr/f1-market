"""Wallet and ledger service for managing user balances."""
from decimal import Decimal
from typing import Optional
from db import db, Wallet, LedgerEntry, User, TransactionType


class InsufficientBalanceError(Exception):
    """Raised when user doesn't have sufficient balance."""
    pass


class WalletService:
    """Service for managing wallets and ledger entries."""
    
    @staticmethod
    def get_or_create_wallet(user_id: int) -> Wallet:
        """
        Get or create a wallet for a user.
        
        Args:
            user_id: User ID
        
        Returns:
            Wallet instance
        """
        wallet = Wallet.query.filter_by(user_id=user_id).first()
        if wallet is None:
            wallet = Wallet(user_id=user_id, balance=Decimal('0'), locked_balance=Decimal('0'))
            db.session.add(wallet)
            db.session.commit()
        return wallet
    
    @staticmethod
    def get_balance(user_id: int) -> Decimal:
        """
        Get available balance for a user.
        
        Args:
            user_id: User ID
        
        Returns:
            Available balance (total balance - locked balance)
        """
        wallet = WalletService.get_or_create_wallet(user_id)
        available = Decimal(str(wallet.balance)) - Decimal(str(wallet.locked_balance))
        return max(available, Decimal('0'))
    
    @staticmethod
    def get_total_balance(user_id: int) -> Decimal:
        """
        Get total balance (including locked) for a user.
        
        Args:
            user_id: User ID
        
        Returns:
            Total balance
        """
        wallet = WalletService.get_or_create_wallet(user_id)
        return Decimal(str(wallet.balance))
    
    @staticmethod
    def get_locked_balance(user_id: int) -> Decimal:
        """
        Get locked balance for a user.
        
        Args:
            user_id: User ID
        
        Returns:
            Locked balance
        """
        wallet = WalletService.get_or_create_wallet(user_id)
        return Decimal(str(wallet.locked_balance))
    
    @staticmethod
    def lock_balance(user_id: int, amount: Decimal) -> bool:
        """
        Lock tokens for a pending transaction.
        
        Args:
            user_id: User ID
            amount: Amount to lock
        
        Returns:
            True if successful
        
        Raises:
            InsufficientBalanceError: If user doesn't have enough balance
        """
        if amount <= 0:
            raise ValueError("Amount must be positive")
        
        wallet = WalletService.get_or_create_wallet(user_id)
        available = Decimal(str(wallet.balance)) - Decimal(str(wallet.locked_balance))
        
        if available < amount:
            raise InsufficientBalanceError(
                f"Insufficient balance. Available: {available}, Required: {amount}"
            )
        
        wallet.locked_balance = Decimal(str(wallet.locked_balance)) + amount
        db.session.commit()
        return True
    
    @staticmethod
    def unlock_balance(user_id: int, amount: Decimal) -> bool:
        """
        Unlock tokens after a transaction is completed or cancelled.
        
        Args:
            user_id: User ID
            amount: Amount to unlock
        
        Returns:
            True if successful
        """
        if amount <= 0:
            raise ValueError("Amount must be positive")
        
        wallet = WalletService.get_or_create_wallet(user_id)
        current_locked = Decimal(str(wallet.locked_balance))
        
        if current_locked < amount:
            # Don't raise error, just unlock what's available
            wallet.locked_balance = Decimal('0')
        else:
            wallet.locked_balance = current_locked - amount
        
        db.session.commit()
        return True
    
    @staticmethod
    def add_ledger_entry(
        user_id: int,
        amount: Decimal,
        transaction_type: TransactionType,
        reference_type: Optional[str] = None,
        reference_id: Optional[int] = None,
        description: Optional[str] = None
    ) -> LedgerEntry:
        """
        Create a ledger entry and update wallet balance atomically.
        
        All token movements must go through this method to maintain audit trail.
        
        Args:
            user_id: User ID
            amount: Amount (positive for credits, negative for debits)
            transaction_type: Type of transaction
            reference_type: Type of reference (e.g., "market", "event")
            reference_id: ID of reference entity
            description: Optional description
        
        Returns:
            Created LedgerEntry instance
        """
        wallet = WalletService.get_or_create_wallet(user_id)
        
        # Create ledger entry
        ledger_entry = LedgerEntry(
            user_id=user_id,
            wallet_id=wallet.id,
            amount=amount,
            transaction_type=transaction_type,
            reference_type=reference_type,
            reference_id=reference_id,
            description=description
        )
        db.session.add(ledger_entry)
        
        # Update wallet balance
        # For debits (negative amount), we also need to reduce locked balance if applicable
        if amount < 0:
            # This is a debit - reduce balance
            abs_amount = abs(amount)
            current_locked = Decimal(str(wallet.locked_balance))
            
            # First reduce from locked balance if available
            if current_locked > 0:
                reduction_from_locked = min(current_locked, abs_amount)
                wallet.locked_balance = current_locked - reduction_from_locked
                abs_amount -= reduction_from_locked
            
            # Then reduce from available balance
            if abs_amount > 0:
                wallet.balance = Decimal(str(wallet.balance)) - abs_amount
        else:
            # This is a credit - increase balance
            wallet.balance = Decimal(str(wallet.balance)) + amount
        
        db.session.commit()
        return ledger_entry
    
    @staticmethod
    def get_ledger_history(user_id: int, limit: int = 100) -> list:
        """
        Get ledger history for a user.
        
        Args:
            user_id: User ID
            limit: Maximum number of entries to return
        
        Returns:
            List of LedgerEntry instances, ordered by created_at desc
        """
        return LedgerEntry.query.filter_by(user_id=user_id)\
            .order_by(LedgerEntry.created_at.desc())\
            .limit(limit)\
            .all()

