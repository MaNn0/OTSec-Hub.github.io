"""passlib 1.7.4 reads bcrypt.__about__.__version__, which bcrypt 4.1+ removed."""
import bcrypt

if not hasattr(bcrypt, "__about__"):
    class _About:
        __version__ = getattr(bcrypt, "__version__", "4.0.1")
    bcrypt.__about__ = _About()
