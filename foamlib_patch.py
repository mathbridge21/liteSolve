# foamlib_patches.py
"""Patches to extend foamlib behavior without modifying library files."""

import foamlib._files._common as _common
import foamlib._files._serialization as _serialization
from numbers import Real

def apply_all_patches():
    _apply_field_keyword_patch()
    _apply_serialization_patch()
    _apply_normalized_patch()

def _apply_field_keyword_patch():
    """Allow 'p0' to be treated as a field keyword in boundaryField."""
    _original = _common._expect_field
    
    def patched(keywords):
        if _original(keywords):
            return True
        match keywords:
            case ("boundaryField", str(), "p0"):
                return True
        return False
    
    _common._expect_field = patched
    _common.FIELD_KEYWORDS = _common._FieldKeywords()

def _apply_serialization_patch():
    """Handle ['uniform', value] lists as field entries without parentheses."""
    import foamlib._files.files as _files_module

    _original = _serialization.dumps
    
    def patched(data, *, keywords=None, format_=None, _tuple_is_keyword_entry=False):
        if (
            isinstance(data, list)
            and len(data) == 2
            and isinstance(data[0], str)
            and (data[0] == "uniform" or data[0].startswith("nonuniform"))
        ):
            k, v = data
            ret = b"\n" if isinstance(k, str) and k[0] == "#" else b""
            if k is not None:
                ret += _original(k, keywords=keywords)
            val = _original(
                v,
                keywords=(*keywords, k) if keywords and k else (() if k is None else None),
                format_=format_,
            )
            if k is not None and val:
                ret += b" "
            ret += val
            if isinstance(k, str) and k[0] == "#":
                ret += b"\n"
            return ret
        return _original(data, keywords=keywords, format_=format_, _tuple_is_keyword_entry=_tuple_is_keyword_entry)
    
    _serialization.dumps = patched
    _files_module.dumps = patched

def _apply_normalized_patch():
    """Allow Real numbers in tuple patterns when parsing strings."""
    from foamlib._files._parsing import parse
    from warnings import warn
    
    _original_normalized = _serialization.normalized
    
    def patched_normalized(
        data,
        /,
        *,
        keywords=None,
        format_=None,
    ):
        # Case: Top-level string (keywords = ())
        if isinstance(data, str) and keywords == ():
            try:
                parsed = parse(data, target=_serialization.StandaloneData)
                match parsed:
                    case str():
                        if not parsed:
                            raise ValueError("found unsupported empty string")
                        return parsed
                    case bool():
                        warn(f"{data!r} will be stored as {parsed!r}", stacklevel=2)
                        return parsed
                    case tuple((str() | bool() | Real(), str() | bool() | Real(), *rest)) if all(
                        isinstance(p, (str, bool, Real)) for p in rest
                    ):
                        warn(f"{data!r} will be stored as {parsed!r}", stacklevel=2)
                        return parsed
                    case _:
                        raise ValueError(f"{data!r} cannot be stored as string (would be stored as {parsed!r})")
            except _serialization.FoamFileDecodeError:
                raise ValueError(f"invalid string: {data!r}") from None
        
        # Case: String in sub-dict (keywords = (_, *_) | None)
        if isinstance(data, str) and (keywords or None) and keywords is not None:
            try:
                parsed = parse(data, target=_serialization.Data)
                match parsed:
                    case str():
                        if not parsed:
                            raise ValueError("found unsupported empty string")
                        return parsed
                    case bool():
                        warn(f"{data!r} will be stored as {parsed!r}", stacklevel=2)
                        return parsed
                    case tuple((str() | bool() | Real(), str() | bool() | Real(), *rest)) if all(
                        isinstance(p, (str, bool, Real)) for p in rest
                    ):
                        warn(f"{data!r} will be stored as {parsed!r}", stacklevel=2)
                        return parsed
                    case _:
                        raise ValueError(f"{data!r} cannot be stored as string (would be stored as {parsed!r})")
            except _serialization.FoamFileDecodeError:
                raise ValueError(f"invalid string: {data!r}") from None
        
        return _original_normalized(data, keywords=keywords, format_=format_)
    
    _serialization.normalized = patched_normalized
