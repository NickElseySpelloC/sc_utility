"""
Spello Consulting Configuration Manager Module.

Management of a YAML log file.
"""

import sys
from pathlib import Path

import yaml
from cerberus import Validator


class SCConfigManager:
    """Loads the configuration from a YAML file, validates it, and provides access to the configuration values."""

    def __init__(self, config_file: str, default_config: dict | None = None, validation_schema: dict | None = None, placeholders: dict | None = None):
        """Initializes the configuration manager."""
        self._config = {}    # Intialise the actual config object
        self.config_file = config_file
        self.logger_function = None  # Placeholder for a logger function

        # Make a note of the app directory
        self.app_dir = self.client_dir = Path(sys.argv[0]).parent.resolve()


        # Determine the file path for the log file
        current_dir = Path.cwd()

        self.config_path = current_dir / self.config_file
        if not self.config_path.exists():
            self.config_path = self.app_dir / self.config_file

        # If the config file doesn't exist and we have a default config, write that to file
        if not self.config_path.exists():
            if default_config is None:
                msg = f"Cannot find config file {self.config_file} and no default config provided."
                raise RuntimeError(msg)

            with Path(self.config_path).open("w", encoding="utf-8") as file:
                yaml.dump(default_config, file)

        # Load the configuration from file, which might be the default
        with Path(self.config_path).open(encoding="utf-8") as file:
            try:
                self._config = yaml.safe_load(file)

            except yaml.YAMLError as e:
                print(f"YAML error in config file {self.config_file}: {e}", file=sys.stderr)

            # Make sure there are no placeholders in the config file, exit if there are
            self.check_for_placeholders(placeholders)

            # If we have a validation schema, validate the config
            if validation_schema is not None:
                v = Validator()

                if not v.validate(self._config, validation_schema):
                    msg = f"Validation error for config file {self.config_file}: {v.errors}"
                    raise RuntimeError(msg)


    def register_logger(self, logger_function: callable) -> None:
        """
        Registers a logger function to be used for logging messages.

        :param logger_function: The function to use for logging messages.
        """
        self.logger_function = logger_function


    def check_for_placeholders(self, placeholders: dict) -> bool:
        """
        Recursively scan self._config for any instances of a key found in placeholders.

        If the keys and values match (including nested), return True.
        :param placeholders: A dictionary of placeholders to check in the config.
        """
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
        """
        Retrieve a value from the config dictionary using a sequence of nested keys.

        Example:
            value = config_mgr.get("DeviceType", "WebsiteAccessKey")

        :param keys: Sequence of keys to traverse the config dictionary.
        :param default: Value to return if the key path does not exist.
        :return: The value if found, otherwise the default.

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
        """
        Returns the logger settings from the config file.

        :param config_section: The section in the config file where logger settings are stored.
        :return: A dictionary of logger settings that can be passed to the SCLogger() class initialization.
        """
        logger_settings = {
            "logfile_name": self.get(config_section, "LogfileName", default="default_logfile.log"),
            "file_verbosity": self.get(config_section, "LogfileVerbosity", default="detailed"),
            "console_verbosity": self.get(config_section, "ConsoleVerbosity", default="summary"),
            "max_lines": self.get(config_section, "LogfileMaxLines", default=10000),
        }
        return logger_settings


    def get_email_settings(self, config_section: str | None = "Email") -> dict:
        """
        Returns the email settings from the config file.

        :param config_section: The section in the config file where email settings are stored.
        :return: A dictionary of email settings or None if email is disabled or not configured correctly.
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

