import logging
from dataclasses import dataclass

def get_logger(filename, verbosity=1, name=None):
    level_dict = {0: logging.DEBUG, 1: logging.INFO, 2: logging.WARNING}
    formatter = logging.Formatter(
        "[%(asctime)s][%(filename)s][%(levelname)s] %(message)s"
    )
    logger = logging.getLogger(name)
    logger.setLevel(level_dict[verbosity])

    fh = logging.FileHandler(filename, "w")
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    # sh = logging.StreamHandler()
    # sh.setFormatter(formatter)
    # logger.addHandler(sh)
    return logger

@dataclass
class GameArgs:
    players: int = 2
    players_card: int = 5
    AIplayer: list = None
    variant: str = "No Variant"
    random_start: bool = True
    start_card: list = None
    allow_drawback: bool = False