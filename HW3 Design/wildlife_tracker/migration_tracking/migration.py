from typing import Any

from wildlife_tracker.migration_tracking.migration_path import MigrationPath

class Migration:

    def __init__(self, migration_id: int, current_location: str, species: str, migration_path: MigrationPath) -> None:
        self.migration_id = migration_id
        self.current_location = current_location
        self.species = species
        self.migration_path = migration_path
    
    def get_migrations() -> list[Migration]:
        pass

    def update_migration_details(migration_id: int, **kwargs: Any) -> None:
        pass

    pass