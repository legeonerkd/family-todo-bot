from .start import router as start_router
from .tasks import router as tasks_router
from .shopping import router as shopping_router
from .family import router as family_router
from .history import router as history_router


def register_handlers(dp):
    dp.include_router(start_router)
    dp.include_router(tasks_router)
    dp.include_router(shopping_router)
    dp.include_router(family_router)
    dp.include_router(history_router)
