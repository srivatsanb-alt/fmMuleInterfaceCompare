import toml
from datetime import datetime


def update_toml_with_changes(file_path, updated_config, user_name):
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d-%H-%M-%S")
    with open(file_path, 'r') as toml_file:
        current_config = toml.load(toml_file)

    def update_and_comment(current, updated, path=""):
        for key, new_value in updated.items():
            full_key = f"{path}.{key}" if path else key
            if isinstance(new_value, dict):
                if key not in current:
                    current[key] = {}
                update_and_comment(current[key], new_value, full_key)
            else:
                if key in current and current[key] != new_value:
                    old_value = current[key]
                    comment = f"{old_value} # Changed by {user_name} at {date_str}"
                    current[f"# {key}"] = comment
                current[key] = new_value

    update_and_comment(current_config, updated_config)

    with open(file_path, 'w') as toml_file:
        toml.dump(current_config, toml_file)

    print(f"Updated {file_path} with changes and added comments.")