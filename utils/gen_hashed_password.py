import hashlib
import click

@click.command()
@click.option("--password", help="Enter the password that needs to be hashed")
def gen_hashed_password(password):
    hashed_password = hashlib.sha256(password.encode("utf-8")).hexdigest()
    print(f"Hashed password: {hashed_password}")

if __name__ == "__main__":
    gen_hashed_password()

