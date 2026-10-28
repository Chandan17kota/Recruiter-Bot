"""Settings loaded from environment variables (and .env if present).

Weights are read as *strings* and parsed into exact Fractions, so "0.60" is
exactly 3/5 and the three weights can be checked to sum to exactly 1.
"""
import os
from dataclasses import dataclass
from fractions import Fraction

from dotenv import load_dotenv


class ConfigError(ValueError):
    """Raised at startup when configuration is invalid."""


@dataclass(frozen=True)
class Weights:
    skills: Fraction
    experience: Fraction
    culture: Fraction

    @classmethod
    def from_strings(cls, skills: str, experience: str, culture: str) -> "Weights":
        try:
            w = cls(Fraction(skills.strip()), Fraction(experience.strip()), Fraction(culture.strip()))
        except (ValueError, ZeroDivisionError) as exc:
            raise ConfigError(f"Weights must be decimal strings, got {skills!r}, {experience!r}, {culture!r}") from exc
        w.validate()
        return w

    def validate(self) -> None:
        if min(self.skills, self.experience, self.culture) < 0:
            raise ConfigError("Weights must be >= 0")
        if self.skills <= 0 or self.experience <= 0:
            raise ConfigError("Skills and experience weights must be > 0 (the brief requires both)")
        if self.skills + self.experience + self.culture != 1:
            total = self.skills + self.experience + self.culture
            raise ConfigError(f"Weights must sum to exactly 1, got {float(total)}")


DEFAULT_WEIGHTS = Weights(Fraction("0.60"), Fraction("0.25"), Fraction("0.15"))


@dataclass(frozen=True)
class Settings:
    database_url: str
    weights: Weights
    statement_timeout_ms: int = 5000
    pool_timeout_s: float = 5.0
    cors_origins: tuple[str, ...] = ()   # empty = no CORS middleware (the Vite dev proxy needs none)


def load_settings(database_url_var: str = "DATABASE_URL") -> Settings:
    load_dotenv()
    url = os.environ.get(database_url_var)
    if not url:
        raise ConfigError(f"{database_url_var} is not set (see .env.example)")
    weights = Weights.from_strings(
        os.environ.get("W_SKILLS", "0.60"),
        os.environ.get("W_EXPERIENCE", "0.25"),
        os.environ.get("W_CULTURE", "0.15"),
    )
    try:
        timeout = int(os.environ.get("DB_STATEMENT_TIMEOUT_MS", "5000"))
    except ValueError as exc:
        raise ConfigError("DB_STATEMENT_TIMEOUT_MS must be an integer") from exc
    if timeout <= 0:
        raise ConfigError("DB_STATEMENT_TIMEOUT_MS must be > 0")
    origins = tuple(o.strip() for o in os.environ.get("CORS_ORIGINS", "").split(",") if o.strip())
    if "*" in origins:
        raise ConfigError("CORS_ORIGINS must list explicit origins, not '*'")
    return Settings(database_url=url, weights=weights, statement_timeout_ms=timeout, cors_origins=origins)
