#!/usr/bin/env python3
"""
Generate a new Ethereum wallet for Hyperliquid
"""
from eth_account import Account
import secrets

def generate_wallet():
    """Generate a new Ethereum wallet"""
    # Generate random private key
    priv = secrets.token_hex(32)
    private_key = "0x" + priv
    
    # Create account
    acct = Account.from_key(private_key)
    
    print("=" * 60)
    print("🔑 New Ethereum Wallet Generated")
    print("=" * 60)
    print(f"\nPrivate Key: {private_key}")
    print(f"Address: {acct.address}")
    print("\n⚠️  IMPORTANT:")
    print("1. Save your private key securely!")
    print("2. Never share it with anyone")
    print("3. Use this for testing only")
    print("4. For mainnet, use a dedicated wallet with limited funds")
    print("=" * 60)

if __name__ == "__main__":
    generate_wallet()
