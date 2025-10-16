"""
Test data generator for Playwright UI validation.
Provides default test inputs for various form fields and scenarios.
"""

import random
import string
from typing import Dict, List, Any

class TestDataGenerator:
    """Generates test data for UI validation scenarios."""
    
    def __init__(self):
        self.test_inputs = {
            "passwords": {
                "weak": ["12345", "abc", "password", "12345678"],
                "medium": ["Password1", "Test123", "User123"],
                "strong": ["StrongPass123!", "SecurePass456@", "ComplexP@ssw0rd"],
                "invalid": ["", " ", "a", "12"]
            },
            "emails": {
                "valid": ["test@example.com", "user@test.org", "admin@domain.net"],
                "invalid": ["test@", "@example.com", "invalid-email", ""]
            },
            "usernames": {
                "valid": ["test_user", "student01", "user123", "admin"],
                "invalid": ["", "a", "user with spaces", "user@domain"],
                "duplicate": ["existing_user", "admin", "test"]
            },
            "names": {
                "valid": ["John Doe", "Jane Smith", "Test User"],
                "invalid": ["", "a", "123", "User@123"]
            },
            "phone_numbers": {
                "valid": ["123-456-7890", "(123) 456-7890", "1234567890"],
                "invalid": ["abc", "123", "123-abc-7890", ""]
            }
        }
    
    def get_test_data(self, field_type: str, scenario: str = "valid") -> List[str]:
        """
        Get test data for a specific field type and scenario.
        
        Args:
            field_type: Type of field (passwords, emails, usernames, etc.)
            scenario: Test scenario (valid, invalid, weak, strong, etc.)
            
        Returns:
            List of test values
        """
        if field_type in self.test_inputs:
            if scenario in self.test_inputs[field_type]:
                return self.test_inputs[field_type][scenario].copy()
            else:
                # Return valid data if scenario not found
                return self.test_inputs[field_type].get("valid", [])
        return []
    
    def get_random_data(self, field_type: str, scenario: str = "valid") -> str:
        """
        Get a random test value for a specific field type and scenario.
        
        Args:
            field_type: Type of field
            scenario: Test scenario
            
        Returns:
            Random test value
        """
        data_list = self.get_test_data(field_type, scenario)
        return random.choice(data_list) if data_list else ""
    
    def generate_dynamic_data(self, field_type: str, count: int = 5) -> List[str]:
        """
        Generate dynamic test data for a field type.
        
        Args:
            field_type: Type of field to generate data for
            count: Number of test values to generate
            
        Returns:
            List of generated test values
        """
        if field_type == "passwords":
            return self._generate_passwords(count)
        elif field_type == "emails":
            return self._generate_emails(count)
        elif field_type == "usernames":
            return self._generate_usernames(count)
        else:
            return []
    
    def _generate_passwords(self, count: int) -> List[str]:
        """Generate various password combinations."""
        passwords = []
        
        # Weak passwords
        for _ in range(count // 3):
            passwords.append(''.join(random.choices(string.digits, k=random.randint(3, 6))))
        
        # Medium passwords
        for _ in range(count // 3):
            passwords.append(''.join(random.choices(string.ascii_letters + string.digits, k=random.randint(6, 10))))
        
        # Strong passwords
        for _ in range(count - len(passwords)):
            chars = string.ascii_letters + string.digits + "!@#$%^&*"
            passwords.append(''.join(random.choices(chars, k=random.randint(8, 15))))
        
        return passwords
    
    def _generate_emails(self, count: int) -> List[str]:
        """Generate various email addresses."""
        domains = ["example.com", "test.org", "domain.net", "sample.co.uk"]
        usernames = ["user", "test", "admin", "student", "demo"]
        
        emails = []
        for _ in range(count):
            username = random.choice(usernames) + str(random.randint(1, 999))
            domain = random.choice(domains)
            emails.append(f"{username}@{domain}")
        
        return emails
    
    def _generate_usernames(self, count: int) -> List[str]:
        """Generate various usernames."""
        prefixes = ["user", "test", "student", "admin", "demo"]
        suffixes = ["123", "01", "2024", "test", ""]
        
        usernames = []
        for _ in range(count):
            prefix = random.choice(prefixes)
            suffix = random.choice(suffixes)
            if suffix:
                usernames.append(f"{prefix}_{suffix}")
            else:
                usernames.append(prefix)
        
        return usernames
    
    def get_form_test_scenarios(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get predefined test scenarios for common form types.
        
        Returns:
            Dictionary of form types and their test scenarios
        """
        return {
            "registration_form": [
                {
                    "name": "Valid Registration",
                    "data": {
                        "username": self.get_random_data("usernames", "valid"),
                        "email": self.get_random_data("emails", "valid"),
                        "password": self.get_random_data("passwords", "strong"),
                        "confirm_password": self.get_random_data("passwords", "strong")
                    },
                    "expected": "success"
                },
                {
                    "name": "Weak Password",
                    "data": {
                        "username": self.get_random_data("usernames", "valid"),
                        "email": self.get_random_data("emails", "valid"),
                        "password": self.get_random_data("passwords", "weak"),
                        "confirm_password": self.get_random_data("passwords", "weak")
                    },
                    "expected": "error"
                },
                {
                    "name": "Invalid Email",
                    "data": {
                        "username": self.get_random_data("usernames", "valid"),
                        "email": self.get_random_data("emails", "invalid"),
                        "password": self.get_random_data("passwords", "strong"),
                        "confirm_password": self.get_random_data("passwords", "strong")
                    },
                    "expected": "error"
                }
            ],
            "login_form": [
                {
                    "name": "Valid Login",
                    "data": {
                        "username": self.get_random_data("usernames", "valid"),
                        "password": self.get_random_data("passwords", "strong")
                    },
                    "expected": "success"
                },
                {
                    "name": "Invalid Credentials",
                    "data": {
                        "username": self.get_random_data("usernames", "invalid"),
                        "password": self.get_random_data("passwords", "invalid")
                    },
                    "expected": "error"
                },
                {
                    "name": "Empty Fields",
                    "data": {
                        "username": "",
                        "password": ""
                    },
                    "expected": "error"
                }
            ]
        }
    
    def validate_input(self, field_type: str, value: str) -> Dict[str, Any]:
        """
        Validate a test input value based on field type.
        
        Args:
            field_type: Type of field
            value: Value to validate
            
        Returns:
            Validation result dictionary
        """
        result = {
            "valid": False,
            "errors": [],
            "strength": "unknown"
        }
        
        if field_type == "password":
            result.update(self._validate_password(value))
        elif field_type == "email":
            result.update(self._validate_email(value))
        elif field_type == "username":
            result.update(self._validate_username(value))
        
        return result
    
    def _validate_password(self, password: str) -> Dict[str, Any]:
        """Validate password strength."""
        errors = []
        strength = "weak"
        
        if len(password) < 6:
            errors.append("Password too short")
        elif len(password) < 8:
            strength = "medium"
        else:
            strength = "strong"
        
        if not any(c.isupper() for c in password):
            errors.append("Missing uppercase letter")
        
        if not any(c.islower() for c in password):
            errors.append("Missing lowercase letter")
        
        if not any(c.isdigit() for c in password):
            errors.append("Missing digit")
        
        if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
            errors.append("Missing special character")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "strength": strength
        }
    
    def _validate_email(self, email: str) -> Dict[str, Any]:
        """Validate email format."""
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        is_valid = bool(re.match(pattern, email))
        
        return {
            "valid": is_valid,
            "errors": ["Invalid email format"] if not is_valid else [],
            "strength": "valid" if is_valid else "invalid"
        }
    
    def _validate_username(self, username: str) -> Dict[str, Any]:
        """Validate username format."""
        errors = []
        
        if len(username) < 3:
            errors.append("Username too short")
        
        if " " in username:
            errors.append("Username cannot contain spaces")
        
        if "@" in username:
            errors.append("Username cannot contain @ symbol")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "strength": "valid" if len(errors) == 0 else "invalid"
        }

# Global instance for easy access
test_data_generator = TestDataGenerator()
