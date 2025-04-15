import importlib.util
import os

def get_rules_module(year: str):
    """
    Carica dinamicamente il modulo delle regole fiscali per l'anno richiesto eseguendo il path assoluto.
    """
    module_path = f"src/fiscal_years/{year}/rules_{year}.py"
    module_name = f"rules_{year}"

    if not os.path.exists(module_path):
        raise ModuleNotFoundError(
            f"Le regole per l'anno {year} non sono state trovate. Verifica che esista {module_path}"
        )

    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
