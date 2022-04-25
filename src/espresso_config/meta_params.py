import inspect
from typing import Any, Sequence, Set, Tuple, Type, Dict

from .node import (
    ConfigNode,
    ConfigFlexNode,
    ConfigParam,
)

__all__ = ['ConfigParamMultiType', 'ConfigParamDictOfConfigNodes']


class _MultiTypeMeta(type):
    types: Tuple[Type]

    def __subclasscheck__(cls, __subclass: type) -> bool:
        return issubclass(__subclass, cls.types)


class _MultiType(metaclass=_MultiTypeMeta):
    types = Tuple[Type]

    def __str__(self):
        types_repr = "|".join(repr(t) for t in self.types)
        return f'{type(self).__name__}({types_repr})'

    def __repr__(self):
        return self.__str__()

    def __instancecheck__(cls, __instance: Any) -> bool:
        return isinstance(__instance, cls.types)

    def __new__(cls, to_cast):
        if not isinstance(to_cast, cls.types):
            # we try to cast one type at the time
            for t in cls.types:
                try:
                    # we immediately return in case
                    # casting is successful
                    return t(to_cast)

                except Exception as e:
                    ...

            msg = (f'`{to_cast}` cannot be casted to ' +
                   ", ".join(t.__name__ for t in cls.types))
            raise ValueError(msg)
        return to_cast

class ConfigParamMultiType(ConfigParam):
    """A ConfigParameter that accepts multiple types.
    casting to parameters is resolved in the order they
    are provided."""
    def __init__(self, *target_types: Sequence[Type]):
        # in case target types is an iterable
        target_types = tuple(t for t in target_types)

        if len(target_types) < 1:
            raise ValueError('Must provide at least one type')

        if any(inspect.isclass(t) and issubclass(t, ConfigNode)
               for t in target_types):
            # TODO: support nested configs
            msg = (f'{type(self).__name__} does not currently accept '
                    'ConfigNode as one of the provided types.')
            raise ValueError(msg)

        self._types = target_types

    @property
    def type(self):
        # because the dynamic class doesn't get pickled, we
        # are good to go here!
        target_type_repr = ', '.join(t.__name__ for t in self._types)
        return type(f'MultiType({target_type_repr})',
                    (_MultiType, ),
                    {'types': self._types})


class _MultiLiteralType(_MultiType):
    literals = Set[Any]

    def __instancecheck__(cls, __instance: Any) -> bool:
        return (super().__instancecheck__(__instance) and
                __instance in cls.literals)

    def __new__(cls, *args, **kwargs):
        obj = super().__new__(*args, **kwargs)
        if obj not in cls.literals:
            raise ValueError(f'{obj} not in {{{" ".join(cls.literals)}}}')
        return obj


class ConfigParamLiteral(ConfigParamMultiType):
    """A ConfigParam that accept specific values."""

    def __init__(self, *literals: Sequence[Any], type_=None):
        if len(literals) < 1:
            raise ValueError('At least one literal must be provided')

        self._literals = literals

        # in case target types is an iterable
        target_types = (type_,) or [type(e) for e in literals]

        super().__init__(*target_types)

    @property
    def type(self):
        target_type_repr = ', '.join(t.__name__ for t in self._types)
        target_lit_repr = f'{{{", ".join(self._literals)}}}'
        return type(
            f'MultiLiteralType({target_type_repr}; {target_lit_repr})',
            (_MultiLiteralType),
            {'types': self._types, 'literals': self._literals}
        )


class _DictOfConfigNodes(ConfigFlexNode):
    node_cls: Type[ConfigNode]

    def __new__(cls,
                config: Dict[str, dict],
                *args,
                **kwargs):
        config_params = {node_name: cls.node_cls(node_config, *args, **kwargs)
                         for node_name, node_config in config.items()}
        return ConfigFlexNode(config_params, *args, **kwargs)


class ConfigParamDictOfConfigNodes(ConfigParam):
    """A special parameter that contains a dictionary of ConfigNodes.
    Useful for when you want to provide a bunch of nodes, but you are
    not sure what the name of keys are. Usage:

    ```python
    from espresso_config import (
        NodeConfig, DictOfConfigNodes, ConfigParam
    )

    class ConfigA(NodeConfig):
        p: ConfigParam(int)

    class RootConfig(NodeConfig):
        dict_of_configs: ConfigParamDictOfConfigNodes(ConfigA) = {}

    ```

    and in the corresponding yaml file:

    ```yaml
    dict_of_configs:
        first_config:
            p: 1
        second_config:
            p: 2
        ...
    ```
    """

    def __init__(self, node_cls: Type[ConfigNode]):
        self.node_cls = node_cls

    @property
    def type(self):
        # because the dynamic class doesn't get pickled, we
        # are good to go here!
        return type(f'DictOfConfigNodes({self.node_cls.__name__})',
                    (_DictOfConfigNodes, ),
                    {'node_cls': self.node_cls})
