# Type Guards in LangGraph

The `langgraph.utils.type_guards` module provides runtime type narrowing helpers that eliminate repeated `isinstance` checks across the codebase.

## Available guards

### `is_checkpoint_saver(obj) -> TypeGuard[BaseCheckpointSaver]`

Returns `True` if `obj` is a concrete `BaseCheckpointSaver` instance. Safe to call even if the `checkpoint` package is not installed (returns `False` on `ImportError`).

```python
from langgraph.utils.type_guards import is_checkpoint_saver

def compile_graph(checkpointer=None):
    if is_checkpoint_saver(checkpointer):
        # type narrowed: checkpointer is BaseCheckpointSaver
        checkpointer.setup()
```

### `is_non_empty_dict(obj) -> TypeGuard[dict[str, object]]`

Returns `True` if `obj` is a dict with at least one entry. Useful for validating state updates before processing.

```python
from langgraph.utils.type_guards import is_non_empty_dict

def apply_update(state_update):
    if not is_non_empty_dict(state_update):
        return  # nothing to apply
    for key, value in state_update.items():
        ...
```

## Adding new guards

All guards in this module must:
1. Accept `object` as the parameter type
2. Return `TypeGuard[T]` for a concrete type `T`
3. Never raise exceptions (catch `ImportError` for optional dependencies)
4. Have a corresponding unit test in `libs/langgraph/tests/unit/test_type_guards.py`
