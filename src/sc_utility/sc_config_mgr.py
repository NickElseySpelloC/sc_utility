"""Spello Consulting Configuration Manager Module.

Management of a YAML log file.
"""

import sys
from pathlib import Path

import yaml
from cerberus import Validator


class SCConfigManager:
    """Loads the configuration from a YAML file, validates it, and provides access to the configuration values."""

    def __init__(self, config_file: str, default_config: dict | None = None, validation_schema: dict | None = None, placeholders: dict | None = None):
        """Initializes the configuration manager.

        Args:
            config_file (str): The relative or absolute path to the configuration file.
            default_config (Optional[dict], optional): A default configuration dict to use if the config file does not exist.
            validation_schema (Optional[dict], optional): A cerberus style validation schema dict to validate the config file against.
            placeholders (Optional[dict], optional): A dictionary of placeholders to check in the config. If any of these are found, a exception will be raised.

        Raises:
            RuntimeError: If the config file does not exist and no default config is provided, or if there are YAML errors in the config file.

        """
        self._config = {}    # Intialise the actual config object
        self.config_file = config_file
        self.config_last_modified = None  # Last modified time of the config file
        self.logger_function = None  # Placeholder for a logger function
        self.validation_schema = validation_schema
        self.placeholders = placeholders

        # Make a note of the app directory
        self.app_dir = self.client_dir = Path(sys.argv[0]).parent.resolve()

        # Determine the file path for the log file
        self.config_path = self.select_file_location(self.config_file)

        # If the config file doesn't exist and we have a default config, write that to file
        if not self.config_path.exists():
            if default_config is None:
                msg = f"Cannot find config file {self.config_file} and no default config provided."
                raise RuntimeError(msg)

            with Path(self.config_path).open("w", encoding="utf-8") as file:
                yaml.dump(default_config, file)

        # Now load the config file
        self.load_config()

    def load_config(self):
        """Load the configuration from the config file specified to the __init__ method.

        Raises:
            RuntimeError: If there are YAML errors in the config file, if placeholders are found, or if validation fails.
        """
        with Path(self.config_path).open(encoding="utf-8") as file:
            try:
                self._config = yaml.safe_load(file)

            except yaml.YAMLError as e:
                msg = f"YAML error in config file {self.config_file}: {e}"
                raise RuntimeError(msg) from e

            else:
                # Make sure there are no placeholders in the config file, exit if there are
                self.check_for_placeholders(self.placeholders)

                # If we have a validation schema, validate the config
                if self.validation_schema is not None:
                    v = Validator()

                    if not v.validate(self._config, self.validation_schema):
                        msg = f"Validation error for config file {self.config_file}: {v.errors}"
                        raise RuntimeError(msg)

        self.config_last_modified = self.config_path.stat().st_mtime

    def check_for_config_changes(self) -> bool:
        """Check if the configuration file has changed. If it has, reload the configuration.

        Returns:
            result (bool): True if the configuration has changed, False otherwise.
        """
        # get the last modified time of the config file
        last_modified = self.config_path.stat().st_mtime

        if self.config_last_modified is None or last_modified > self.config_last_modified:
            # The config file has changed, reload it
            self.load_config()
            self.config_last_modified = last_modified
            return True

        return False

    def select_file_location(self, file_name: str) -> Path:
        """Selects the file location for the given file name.

        Args:
            file_name (str): The name of the file to locate. Can be just a file name, or a relative or absolute path.

        Returns:
            file_path (Path): The full path to the file as a Path object. If the file does not exist in the current directory, it will look in the script directory.
        """
        # Check to see if file_name is a full path or just a file name
        file_path = Path(file_name)

        # Check if file_name is an absolute path, return this even if it does not exist
        if file_path.is_absolute():
            return file_path

        # Check if file_name contains any parent directories (i.e., is a relative path)
        # If so, return this even if it does not exist
        if file_path.parent != Path("."):  # noqa: PTH201
            # It's a relative path
            return (Path.cwd() / file_path).resolve()

        # Otherwise, assume it's just a file name and look for it in the current directory and the script directory
        current_dir = Path.cwd()
        app_dir = self.client_dir = Path(sys.argv[0]).parent.resolve()
        file_path = current_dir / file_name
        if not file_path.exists():
            file_path = app_dir / file_name
        return file_path

    def register_logger(self, logger_function: callable) -> None:
        """Registers a logger function to be used for logging messages.

        Args:
            logger_function (callable): The function to use for logging messages.
        """
        self.logger_function = logger_function

    def check_for_placeholders(self, placeholders: dict) -> bool:
        """Recursively scan self._config for any instances of a key found in placeholders.

        If the keys and values match (including nested), return True.

        Args:
            placeholders (dict): A dictionary of placeholders to check in the config.

        Raises:
            RuntimeError: If any placeholder is found in the config file, an exception will be raised with a message indicating the placeholder and its value.

        Returns:
            result (bool): True if any placeholders are found in the config, otherwise False.
        """  # noqa: DOC502
        def recursive_check(config_section, placeholder_section):
            for key, placeholder_value in placeholder_section.items():
                if key in config_section:
                    config_value = config_section[key]
                    if isinstance(placeholder_value, dict) and isinstance(config_value, dict):
                        if recursive_check(config_value, placeholder_value):
                            return True
                    elif config_value == placeholder_value:
                        msg = f"Placeholder value '{key}: {placeholder_value}' found in config file. Please fix this."
                        raise RuntimeError(msg)
            return False

        if placeholders is None:
            return False

        return recursive_check(self._config, placeholders)

    def get(self, *keys, default=None):
        """Retrieve a value from the config dictionary using a sequence of nested keys.

        Example:
            value = config_mgr.get("DeviceType", "WebsiteAccessKey")

        Args:
            keys (*keys): Sequence of keys to traverse the config dictionary.
            default (Optional[variable], optional): Value to return if the key path does not exist.

        Returns:
            value (variable): The value if found, otherwise the default.

        """
        value = self._config
        try:
            for key in keys:
                value = value[key]
        except (KeyError, TypeError):
            return default
        else:
            return value

    def get_logger_settings(self, config_section: str | None = "Files") -> dict:
        """Returns the logger settings from the config file.

        Args:
            config_section (Optional[str], optional): The section in the config file where logger settings are stored.

        Returns:
            settings (dict): A dictionary of logger settings that can be passed to the SCLogger() class initialization.
        """
        logger_settings = {
            "logfile_name": self.get(config_section, "LogfileName", default="default_logfile.log"),
            "file_verbosity": self.get(config_section, "LogfileVerbosity", default="detailed"),
            "console_verbosity": self.get(config_section, "ConsoleVerbosity", default="summary"),
            "max_lines": self.get(config_section, "LogfileMaxLines", default=10000),
            "log_process_id": self.get(config_section, "LogProcessId", default=False),
        }
        return logger_settings

    def get_email_settings(self, config_section: str | None = "Email") -> dict:
        """Returns the email settings from the config file.

        Args:
            config_section (Optional[str], optional): The section in the config file where email settings are stored.

        Returns:
            settings (dict): A dictionary of email settings or None if email is disabled or not configured correctly.
        """
        # fir check to see if we have an EnableEmail setting
        enable_email = self.get(config_section, "EnableEmail", default=True)
        if not enable_email:
            return None

        email_settings = {
            "SendEmailsTo": self.get(config_section, "SendEmailsTo"),
            "SMTPServer": self.get(config_section, "SMTPServer"),
            "SMTPUsername": self.get(config_section, "SMTPUsername"),
            "SMTPPassword": self.get(config_section, "SMTPPassword"),
            "SubjectPrefix": self.get(config_section, "SubjectPrefix"),
        }

        # Only return true if all the required email settings have been specified (excluding SubjectPrefix)
        required_fields = {k: v for k, v in email_settings.items() if k != "SubjectPrefix"}
        if all(required_fields.values()):
            return email_settings

        return None
