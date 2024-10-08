from typing import Any, Optional
#submission
class Animal:

    def __init__(self, animal_id: int, species: str, age: Optional[int] = None, 
                health_status: Optional[str] = None) -> None:
         self.animal_id = animal_id
         self.age = age
         self.health_status = health_status
         self.species = species

    def get_animal_details(animal_id) -> dict[str, Any]:
        pass

    def update_animal_details(animal_id: int, **kwargs: Any) -> None:
        pass