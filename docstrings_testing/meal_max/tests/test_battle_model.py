import pytest

from meal_max.models.battle_model import BattleModel
from meal_max.models.kitchen_model import Meal


@pytest.fixture()
def battle_model():
    """Fixture to provide a new instance of BattleModel for each test."""
    return BattleModel()

@pytest.fixture
def mock_update_meal_stats(mocker):
    """Mock the update_meal_stats function for testing purposes."""
    return mocker.patch("meal_max.models.battle_model.update_meal_stats")

"""Fixtures providing sample meals for the tests."""
@pytest.fixture
def sample_meal1():
    return Meal(1, 'Meal 2', 'Cuisine 1', 10.0, 'MED')

@pytest.fixture
def sample_meal2():
    return Meal(2, 'Meal 2', 'Cuisine 2', 20.0, 'HIGH')

@pytest.fixture
def sample_meal3():
    return Meal(3, 'Meal 3', 'Cuisine 3', 15.0, 'LOW')

@pytest.fixture
def sample_battle(sample_meal1, sample_meal2):
    return [sample_meal1, sample_meal2]

def test_battle(battle_model, sample_meal1):
    """Test a battle between 2 meals."""

    battle_model.combatants.extend(sample_battle)

    assert len(battle_model.combattants) == 2
    assert battle_model.combatants[0].meal = "Meal 1"
    assert battle_model.combatants[0].meal = "Meal 2"

def test_clear_combatants(battle_model, sample_battle):
    """Test clearing the list of combatants."""

    battle_model.combatants.extend(sample_battle)
    assert len(battle_model.combatants) == 2

    battle_model.clear_combatants()
    assert len(battle_model.combatants) == 0, "Combatants should be empty after clearing"

def test_get_battle_score(battle_model, sample_meal1):
    """Test getting the score of a meal."""

    expected_score = 88
    calculated_score = battle_model.get_battle_score(sample_meal1)
    battle_model.assertEqual(expected_score, calculated_score)

def test_get_combatants(battle_model, sample_battle):
    """Test retrieving all meals from combatants."""

    #Ensure Combatants is empty
    battle_model.clear_combatants()

    #Add sample meals to combatants
    battle_model.combatants.extend(sample_battle)
    all_combatants = battle_model.get_combatants()

    assert len(all_combatants) == 2
    assert all_combatants[0].id == 1, f"Expected first combatant ID {sample_battle[0].id}, got {all_combatants[0].id}"
    assert all_combatants[1].id == 2, f"Expected second combatant ID {sample_battle[1].id}, got {all_combatants[1].id}"

def test_prep_combatant(battle_model, sample_meal1):
    """Test adding a meal to combatants"""

    #Ensure Combatants is empty
    battle_model.clear_combatants()
    battle_model.prep_combatant(sample_meal1)

    assert len(battle_model.combatants) == 1, "Expected 1 meal in combatants after adding"
    assert battle_model.combatants[0].id == 1, f"Expected combatant ID {sample_meal1.id}, got {battle_model.combatants[0].id}"

def test_prep_combatant_no_space(battle_model, sample_meal1, sample_meal2, sample_meal3, caplog):
    """Test error when adding a meal to combatants, but combatants already contains 2 meals"""

    #Add 2 meals to combatant
    battle_model.prep_combatant(sample_meal1)
    battle_model.prep_combatant(sample_meal2)

    with pytest.raises(ValueError, match="Combatant list is full, cannot add more combatants."):
        battle_model.prep_combatant(sample_meal3)

    assert "Attempted to add combatant" in caplog.text, "expected error message when adding a meal to a full combatants list"