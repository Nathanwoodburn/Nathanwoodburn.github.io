import os
import json

if not os.path.exists(".well-known/wallets"):
    os.makedirs(".well-known/wallets")


def addCoin(token: str, name: str, address: str):
    with open(".well-known/wallets/" + token.upper(), "w") as f:
        f.write(address)

    with open(".well-known/wallets/.coins", "r") as f:
        coins = json.load(f)

    coins[token.upper()] = f"{name} ({token.upper()})"
    with open(".well-known/wallets/.coins", "w") as f:
        f.write(json.dumps(coins, indent=4))


def addDomain(token: str, domain: str):
    with open(".well-known/wallets/.domains", "r") as f:
        domains = json.load(f)

    domains[token.upper()] = domain
    with open(".well-known/wallets/.domains", "w") as f:
        f.write(json.dumps(domains, indent=4))


if __name__ == "__main__":
    # Ask user for token
    token = input("Enter token symbol: ")
    name = input("Enter token name: ")
    address = input("Enter wallet address: ")
    addCoin(token, name, address)

    if input("Do you want to add a domain? (y/n): ").lower() == "y":
        domain = input("Enter domain: ")
        addDomain(token, domain)
