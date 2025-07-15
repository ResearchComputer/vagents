import inspect
import dataclasses


def dataclass_to_cli(func):
    """
    Converts a function taking a dataclass as its first argument into a
    dataclass that can be called via `typer` as a CLI.
    Additionally, the --config option will load a yaml configuration before the
    other arguments.
    Modified from:
    - https://github.com/tiangolo/typer/issues/197
    A couple related issues:
    - https://github.com/tiangolo/typer/issues/153
    - https://github.com/tiangolo/typer/issues/154
    """

    # The dataclass type is the first argument of the function.
    sig = inspect.signature(func)

    param = list(sig.parameters.values())
    dataclass_params = [x for x in param if dataclasses.is_dataclass(x.annotation)]

    if not dataclass_params:
        # No dataclass parameter found, return original function
        return func

    cls = dataclass_params[0].annotation  # Use the first dataclass found
    remaining_params = [x for x in param if not dataclasses.is_dataclass(x.annotation)]

    def wrapped(**kwargs):
        conf = {}
        # CLI options override the config file.
        # if the k in kwargs are in cls, then we update the conf
        dataclass_kwargs = {
            k: v for k, v in kwargs.items() if k in cls.__dataclass_fields__
        }
        conf.update(dataclass_kwargs)
        # Convert back to the original dataclass type.
        arg = cls(**conf)

        # Get values for remaining parameters in the correct order
        remaining_kwargs = {
            k: v for k, v in kwargs.items() if k not in cls.__dataclass_fields__
        }

        # Build arguments in the correct order based on original function signature
        call_args = []
        call_kwargs = {}

        for param_obj in param:
            param_name = param_obj.name
            if dataclasses.is_dataclass(param_obj.annotation):
                call_args.append(arg)
            elif param_name in remaining_kwargs:
                call_args.append(remaining_kwargs[param_name])
            elif param_obj.default != inspect.Parameter.empty:
                # Use default value if available
                call_kwargs[param_name] = param_obj.default
            # Skip if parameter not provided and has no default

        return func(*call_args, **call_kwargs)

    # To construct the signature, we remove the first argument (self)
    # from the dataclass __init__ signature.
    signature = inspect.signature(cls.__init__)
    parameters = list(signature.parameters.values())
    if len(parameters) > 0 and parameters[0].name == "self":
        del parameters[0]

    # Add the --config option to the signature.
    # When called through the CLI, we need to set defaults via the YAML file.
    # Otherwise, every field will get overwritten when the YAML is loaded.

    parameters = [p for p in remaining_params if p.name != "config"] + [
        p for p in parameters if p.name != "config"
    ]

    # The new signature is compatible with the **kwargs argument.
    wrapped.__signature__ = signature.replace(parameters=parameters)
    # The docstring is used for the explainer text in the CLI.
    wrapped.__doc__ = (func.__doc__ or "") + "\n"
    wrapped.__name__ = func.__name__
    return wrapped
