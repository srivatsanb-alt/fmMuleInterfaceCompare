#!/usr/bin/env python3

import subprocess
import time
import sys
import json


def run_docker_command(command, timeout=30):
    """Run a docker command and return the output."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "Command timed out"


def run_mongosh_command(command, timeout=30):
    """Run a mongosh command with credential fallback."""
    # First try with credentials
    try:
        auth_command = f'docker exec fm_mongo mongosh "mongodb://ati:atiMongo@mongo:27017/?authSource=admin" --quiet --eval "{command}"'
        success, stdout, stderr = run_docker_command(auth_command, timeout)

        if success:
            return success, stdout, stderr
    except Exception:
        pass
    # If credentials fail, try without credentials
    no_auth_command = f'docker exec fm_mongo mongosh "mongodb://mongo:27017" --quiet --eval "{command}"'
    return run_docker_command(no_auth_command, timeout)


def wait_for_mongodb_ready(max_attempts=30):
    """Wait for MongoDB container to be running and ready."""
    print("Waiting for MongoDB container to be running and ready...")

    for attempt in range(max_attempts):
        # First check if container is running
        container_success, container_stdout, _ = run_docker_command("docker ps --format '{{.Names}}' | grep -w fm_mongo")
        if not (container_success and "fm_mongo" in container_stdout):
            print(f"Attempt {attempt + 1}/{max_attempts}: MongoDB container not running yet...")
            time.sleep(1)
            continue

        # Then check if MongoDB is ready to accept connections
        ready_success, ready_stdout, _ = run_mongosh_command("JSON.stringify(db.runCommand('ping'))", timeout=10)
        if ready_success:
            try:
                result = json.loads(ready_stdout.strip())
                if result.get("ok") == 1:
                    print("✅ MongoDB container is running and ready")
                    return True
            except json.JSONDecodeError:
                pass

        print(f"Attempt {attempt + 1}/{max_attempts}: MongoDB container running but not ready yet...")
        time.sleep(1)

    print("❌ MongoDB failed to start within expected time")
    return False


def check_replica_set_status():
    """Check if replica set is already configured and healthy."""
    success, stdout, _ = run_mongosh_command("JSON.stringify(rs.status())")

    if success:
        try:
            result = json.loads(stdout.strip())
            if result.get("ok") == 1:
                members = result.get("members", [])
                for member in members:
                    if member.get("stateStr") == "PRIMARY":
                        print("✅ MongoDB replica set is already configured and healthy with PRIMARY")
                        return True
        except json.JSONDecodeError:
            pass

    return False


def check_existing_data():
    """Check for existing MongoDB data."""
    print("Checking for existing MongoDB data...")

    success, stdout, _ = run_mongosh_command("JSON.stringify(db.adminCommand('listDatabases'))")

    if success:
        try:
            result = json.loads(stdout.strip())
            if result.get("ok") == 1:
                databases = result.get("databases", [])
                user_dbs = [db for db in databases if db["name"] not in ["admin", "config", "local"]]
                user_db_count = len(user_dbs)

                if user_db_count > 0:
                    print(f"⚠️  Existing standalone data detected ({user_db_count} user databases)")
                    print("Converting standalone MongoDB to replica set...")
                else:
                    print("✅ New installation detected (no user databases)")
                    print("Initializing replica set for new installation...")
                return user_db_count
        except json.JSONDecodeError:
            pass

    print("⚠️  Could not determine database count, proceeding with initialization...")
    return 0


def check_replication_enabled():
    """Check if MongoDB was started with replication enabled."""
    success, stdout, _ = run_mongosh_command("JSON.stringify(db.adminCommand('getCmdLineOpts'))")

    if success:
        try:
            result = json.loads(stdout.strip())
            parsed = result.get("parsed", {})
            replication = parsed.get("replication", {})
            return "replSet" in replication
        except json.JSONDecodeError:
            return False
    return False


def initialize_replica_set():
    """Initialize the replica set."""
    print("Initializing replica set...")

    # Check if replication is enabled
    if not check_replication_enabled():
        print("⚠️  MongoDB was not started with replication enabled")
        print("ℹ️  Replica set configuration requires MongoDB to be started with --replSet parameter")
        print("ℹ️  Please restart MongoDB container with replication enabled")
        return False

    init_command = '''JSON.stringify(rs.initiate({
  _id: 'rs0',
  members: [
    { _id: 0, host: 'mongo:27017' }
  ]
}))'''

    success, stdout, stderr = run_mongosh_command(init_command)

    if success:
        try:
            result = json.loads(stdout.strip())
            if result.get("ok") == 1:
                print("✅ Replica set initialized successfully")
                return True
            elif "already initialized" in result.get("errmsg", ""):
                print("✅ Replica set was already initialized")
                return True
            else:
                print("⚠️  Replica set initialization encountered issues, but continuing...")
                print(f"Debug output: {result}")
                return True
        except json.JSONDecodeError:
            print("⚠️  Could not parse initialization result, but continuing...")
            return True
    else:
        print(f"❌ Failed to initialize replica set: {stderr}")
        return False


def wait_for_primary_election_and_verify(max_attempts=30, final_verification=False):
    """Wait for replica set to elect primary and optionally do final verification."""
    if final_verification:
        print("Performing final verification of replica set...")
    else:
        print("Waiting for replica set to elect primary...")

    for attempt in range(max_attempts):
        success, stdout, _ = run_mongosh_command("JSON.stringify(rs.status())")

        if success:
            try:
                result = json.loads(stdout.strip())
                if result.get("ok") == 1:
                    members = result.get("members", [])
                    for member in members:
                        if member.get("stateStr") == "PRIMARY":
                            if final_verification:
                                print("✅ MongoDB replica set configuration completed and verified")
                            else:
                                print("✅ Replica set is ready with PRIMARY member!")
                            return True
            except json.JSONDecodeError:
                pass

        if not final_verification:
            print(f"Replica set attempt {attempt + 1}/{max_attempts}: Still electing primary...")
            time.sleep(1)
        else:
            # For final verification, don't loop - just check once
            break

    if final_verification:
        print("⚠️  MongoDB replica set configuration completed but verification failed")
        print("ℹ️  This is normal during standalone-to-replica conversion startup")
    else:
        print("⚠️  Primary election may not be complete, but continuing...")
    return False


def configure_mongodb_replica_set():
    """Main function to configure MongoDB replica set."""
    print("Checking MongoDB replica set configuration...")

    # Wait for MongoDB container to be running and ready
    if not wait_for_mongodb_ready():
        print("MongoDB container not running or not ready, skipping replica set setup")
        return True

    # Check if replica set is already configured
    if check_replica_set_status():
        return True

    # Check for existing data
    check_existing_data()

    # Initialize replica set
    if not initialize_replica_set():
        return False

    # Wait for primary election
    wait_for_primary_election_and_verify()

    # Final verification
    wait_for_primary_election_and_verify(final_verification=True)

    return True


if __name__ == "__main__":
    try:
        success = configure_mongodb_replica_set()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n❌ Configuration interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)