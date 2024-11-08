from contextlib import contextmanager
import re
import sqlite3

import pytest

from meal_max.models.kitchen_model import (
    Meal,
    create_meal,
    clear_meals,
    delete_meal,
    get_leaderboard,
    get_meal_by_id,
    get_meal_by_name,
    update_meal_stats
)

def normalize_whitespace(sql_query: str) -> str:
    return re.sub(r'\s+', ' ', sql_query).strip()

# Mocking the database connection for tests
@pytest.fixture
def mock_cursor(mocker):
    mock_conn = mocker.Mock()
    mock_cursor = mocker.Mock()

    # Mock the connection's cursor
    mock_conn.cursor.return_value = mock_cursor
    mock_cursor.fetchone.return_value = None  # Default return for queries
    mock_cursor.fetchall.return_value = []
    mock_conn.commit.return_value = None

    # Mock the get_db_connection context manager from sql_utils
    @contextmanager
    def mock_get_db_connection():
        yield mock_conn  # Yield the mocked connection object

    mocker.patch("meal_max.models.kitchen_model.get_db_connection", mock_get_db_connection)

    return mock_cursor  # Return the mock cursor so we can set expectations per test

def test_create_meal(mock_cursor):
    """Test creating a new meal in the catalog."""

    #Call the function to create a new meal
    create_meal(meal="Meal Name", cuisine="Cuisine Type", price=100.50, difficulty="HIGH")

    expected_query = normalize_whitespace("""
        INSERT INTO meals (meal, cuisine, price, difficulty)
        VALUES (?, ?, ?, ?)
    """)

    actual_query = normalize_whitespace(mock_cursor.execute.call_args[0][0])

    #Assert that the SQL query was correct
    assert actual_query == expected_query, "The SQL query did not match the expected structure."

    #Extract the arguments used in the SQL call (second element of call_args)
    actual_arguments = mock_cursor.execute.call_args[0][1]

    #Assert that the SQL query was executed with the correct arguments
    expected_arguments = ("Meal Name", "Cuisine Type", 100.50, "HIGH")
    assert actual_arguments == expected_arguments, f"The SQL query arguments did not match. Expected {expected arguments}, got {actual_arguments}."

def test_create_meal_duplicate(mock_cursor):
    """Test creating a meal with a duplicate name (should raise an error)."""

    # Simulate that the database will raise an IntegrityError due to a duplicate entry
    mock_cursor.execute.side_effect = sqlite3.IntegrityError("UNIQUE constraint failed: meals.meal")

    # Expect the function to raise a ValueError with a specific message when handling the IntegrityError
    with pytest.raises(ValueError, match="Meal with name 'Meal A' already exists."):
        create_meal(meal="Meal A", cuisine="Cuisine A", price=20.00, difficulty="HIGH")

def test_create_meal_invalid_price(mock_cursor):
    """Test error when trying to create a meal with an invalid price (e.g., negative price)"""

    # Attempt to create a meal with a negative price
    with pytest.raises(ValueError, match="Invalid meal price: -20.00 \(must be a positive float\)."):
        create_meal(meal="Meal A", cuisine="Cuisine A", price=-20.00, difficulty="HIGH")

def test_create_meal_invalid_difficulty(mock_cursor):
    """Test error when trying to create a meal with an invalid difficulty (Not 'LOW', 'MED', or 'HIGH')."""

    # Attempt to create a meal with a invalid difficulty
    with pytest.raises(ValueError, match="Invalid meal difficulty: 'MEDIUM' \(must be 'LOW', 'MED', or 'HIGH'\)."):
        create_meal(meal="Meal A", cuisine="Cuisine A", price=20.00, difficulty="MEDIUM")    

def test_clear_meals(mock_cursor):
    """Test clearing the entire meal table (removes all meals)."""

    #Mock the file reading
    mocker.path.dict('os.environ', {'SQL_CREATE_TABLE_PATH': 'sql/create_meal_table.sql'})
    mock_open = mocker.patch('builtins.open', mocker.mock_open(read_data="The body of the create statement"))

    # Call the clear_database function
    clear_meals()

    # Ensure the file was opened using the environment variable's path
    mock_open.assert_called_once_with('sql/create_meal_table.sql', 'r')

    # Verify that the correct SQL script was executed
    mock_cursor.executescript.assert_called_once()

def test_delete_meal(mock_cursor):
    """Test soft deleting a meal from the table by meal ID"""

    # Simulate that the meal exists (id = 1)
    mock_cursor.fetchone.return_value = ([False])

    # Call the delete_meal function
    delete_meal(1)

    # Normalize the SQL for both queries (SELECT and UPDATE)
    expected_select_sql = normalize_whitespace("SELECT deleted FROM meals WHERE id = ?")
    expected_update_sql = normalize_whitespace("UPDATE meals SET deleted = TRUE WHERE id = ?")

    # Access both calls to `execute()` using `call_args_list`
    actual_select_sql = normalize_whitespace(mock_cursor.execute.call_args_list[0][0][0])
    actual_update_sql = normalize_whitespace(mock_cursor.execute.call_args_list[1][0][0])

    # Ensure the correct SQL queries were executed
    assert actual_select_sql == expected_select_sql, "The SELECT query did not match the expected structure."
    assert actual_update_sql == expected_update_sql, "The UPDATE query did not match the expected structure."

    # Ensure the correct arguments were used in both SQL queries
    expected_select_args = (1,)
    expected_update_args = (1,)

    actual_select_args = mock_cursor.execute.call_args_list[0][0][1]
    actual_update_args = mock_cursor.execute.call_args_list[1][0][1]

    assert actual_select_args == expected_select_args, f"The SELECT query arguments did not match. Expected {expected_select_args}, got {actual_select_args}."
    assert actual_update_args == expected_update_args, f"The UPDATE query arguments did not match. Expected {expected_update_args}, got {actual_update_args}."

def test_delete_meal_bad_id(mock_cursor):
    """Test error when trying to delete a non-existent meal."""

    # Simulate that no meal exists with the given ID
    mock_cursor.fetchone.return_value = None

    # Expect a ValueError when attempting to delete a non-existent meal
    with pytest.raises(ValueError, match="Meal with ID 999 not found"):
        delete_meal(999)

def test_delete_meal_already_deleted(mock_cursor):
    """Test error when trying to delete a meal that's already marked as deleted."""

    # Simulate that the meal exists but is already marked as deleted
    mock_cursor.fetchone.return_value = ([True])

    # Expect a ValueError when attempting to delete a meal that's already been deleted
    with pytest.raises(ValueError, match="Meal with ID 999 has already been deleted"):
        delete_meal(999)

def test_get_leaderboard_sorted_by_wins(mock_cursor):
    """Test retrieving all meals ordered by total wins"""

    #Simulate that there are multiple meals in the database
    mock_cursor.fetchall.return_value = [
        (1, "Meal A", "Cuisine A", 25.50, "MED", 40, 30, .75),
        (2, "Meal B", "Cuisine B", 50.10, "HIGH", 100, 50, .5),
        (3, "Meal C", "Cuisine C", 30.00, "LOW", 50, 5, .10)
    ]

    #Call the get_leaderboard function witch sort_by = "wins"
    meals = get_leaderboard(sort_by="wins")

    #Ensure the results are sorted by wins
    expected_result = [
        {"id": 2, "meal": "Meal B", "Cuisine": "Cuisine B", "price": 50.10, "difficulty": "HIGH", "battles": 100, "wins": 50, "win_pct": .50},
        {"id": 1, "meal": "Meal A", "Cuisine": "Cuisine A", "price": 25.50, "difficulty": "MED", "battles": 40, "wins": 30, "win_pct": .75},
        {"id": 3, "meal": "Meal C", "Cuisine": "Cuisine C", "price": 30.00, "difficulty": "LOW", "battles": 50, "wins": 5, "win_pct": .10},
    ]

    assert meals == expected_result, f"Expected {expected_result}, but got {meals}"

    #Ensure the SQL query was executed correctly
    expected_query = normalize_whitespace("""
        SELECT id, meal, cuisine, price, difficulty, battles, wins, win_pct
        FROM meals
        WHERE deleted = FALSE
        ORDER BY wins DESC
    """)
    actual_query == expected_query, "The SQL query did not match the expected structure"

def test_get_leaderboard_sorted_by_win_pct(mock_cursor):
    """Test retrieving all meals ordered by win percentage"""

    #Simulate that there are multiple meals in the database
    mock_cursor.fetchall.return_value = [
        (1, "Meal A", "Cuisine A", 25.50, "MED", 40, 30, .75),
        (2, "Meal B", "Cuisine B", 50.10, "HIGH", 100, 50, .5),
        (3, "Meal C", "Cuisine C", 30.00, "LOW", 50, 5, .10)
    ]

    #Call the get_leaderboard function witch sort_by = "wins"
    meals = get_leaderboard(sort_by="win_pct")

    #Ensure the results are sorted by wins
    expected_result = [
        {"id": 1, "meal": "Meal A", "Cuisine": "Cuisine A", "price": 25.50, "difficulty": "MED", "battles": 40, "wins": 30, "win_pct": .75},
        {"id": 2, "meal": "Meal B", "Cuisine": "Cuisine B", "price": 50.10, "difficulty": "HIGH", "battles": 100, "wins": 50, "win_pct": .50},
        {"id": 3, "meal": "Meal C", "Cuisine": "Cuisine C", "price": 30.00, "difficulty": "LOW", "battles": 50, "wins": 5, "win_pct": .10}
    ]

    assert meals == expected_result, f"Expected {expected_result}, but got {meals}"

    #Ensure the SQL query was executed correctly
    expected_query = normalize_whitespace("""
        SELECT id, meal, cuisine, price, difficulty, battles, wins, win_pct
        FROM meals
        WHERE deleted = FALSE
        ORDER BY win_pct DESC
    """)
    actual_query == expected_query, "The SQL query did not match the expected structure"

def test_get_meal_by_id(mock_cursor):
    """Test retrieval of a meal by ID."""

    # Simulate that the meal exists (id = 1)
    mock_cursor.fetchone.return_value = (1, "Meal A", "Cuisine A", 20.00, "HIGH", False)

    # Call the function and check the result
    result = get_meal_by_id(1)

    # Expected result based on the simulated fetchone return value
    expected_result = Meal(1, "Meal A", "Cuisine A", 20.00, "HIGH")

    # Ensure the result matches the expected output
    assert result == expected_result, f"Expected {expected_result}, got {result}"

    # Ensure the SQL query was executed correctly
    expected_query = normalize_whitespace("SELECT id, meal, cuisine, price, difficulty, deleted FROM meals WHERE id = ? AND deleted = false")
    actual_query = normalize_whitespace(mock_cursor.execute.call_args[0][0])

    # Assert that the SQL query was correct
    assert actual_query == expected_query, "The SQL query did not match the expected structure."

    # Extract the arguments used in the SQL call
    actual_arguments = mock_cursor.execute.call_args[0][1]

    # Assert that the SQL query was executed with the correct arguments
    expected_arguments = (1,)
    assert actual_arguments == expected_arguments, f"The SQL query arguments did not match. Expected {expected_arguments}, got {actual_arguments}."

def test_get_meal_by_id_bad_id(mock_cursor):
    """Test retrieval of a meal by ID when ID is invalid."""

    # Simulate that no meal exists for the given ID
    mock_cursor.fetchone.return_value = None

    # Expect a ValueError when the meal is not found
    with pytest.raises(ValueError, match="Meal with ID 999 not found"):
        get_meal_by_id(999)

def test_get_meal_by_id_deleted_meal(mock_cursor):
    """Test error when trying to get a deleted meal."""

    # Simulate that the meal exists but is marked as deleted (id = 1)
    mock_cursor.fetchone.return_value = [True]

    # Expect a ValueError when attempting to update a deleted meal
    with pytest.raises(ValueError, match="Meal with ID 1 has been deleted"):
        get_meal(1)

def test_get_meal_by_name(mock_cursor):
    """Test retrieval of a meal by name."""

    # Simulate that the meal exists (meal = 'Meal A')
    mock_cursor.fetchone.return_value = (1, "Meal A", "Cuisine A", 20.00, "HIGH", False)

    # Call the function and check the result
    result = get_meal_by_name("Meal A")

    # Expected result based on the simulated fetchone return value
    expected_result = Meal(1, "Meal A", "Cuisine A", 20.00, "HIGH")

    # Ensure the result matches the expected output
    assert result == expected_result, f"Expected {expected_result}, got {result}"

    # Ensure the SQL query was executed correctly
    expected_query = normalize_whitespace("SELECT id, meal, cuisine, price, difficulty, deleted FROM meals WHERE name = ? AND deleted = false")
    actual_query = normalize_whitespace(mock_cursor.execute.call_args[0][0])

    # Assert that the SQL query was correct
    assert actual_query == expected_query, "The SQL query did not match the expected structure."

    # Extract the arguments used in the SQL call
    actual_arguments = mock_cursor.execute.call_args[0][1]

    # Assert that the SQL query was executed with the correct arguments
    expected_arguments = (1,)
    assert actual_arguments == expected_arguments, f"The SQL query arguments did not match. Expected {expected_arguments}, got {actual_arguments}."

def test_get_meal_by_name_bad_name(mock_cursor):
    """Test retrieval of a meal by name when name is invalid."""

    # Simulate that no meal exists for the given name
    mock_cursor.fetchone.return_value = None

    # Expect a ValueError when the meal is not found
    with pytest.raises(ValueError, match="Meal with name 'Meal 999' not found"):
        get_meal_by_name("Meal 999")

def test_get_meal_by_name_deleted_meal(mock_cursor):
    """Test error when trying to get a deleted meal."""

    # Simulate that the meal exists but is marked as deleted (name = 'Meal A')
    mock_cursor.fetchone.return_value = [True]

    # Expect a ValueError when attempting to update a deleted meal
    with pytest.raises(ValueError, match="Meal with name 'Meal A' has been deleted"):
        get_meal_by_name("Meal A")

def test_update_meal_stats_win(mock_cursor):
    """Test updating battle stats of a meal after a win."""

    # Simulate that the meal exists and is not deleted (id = 1)
    mock_cursor.fetchone.return_value = [False]

    # Call the update_meal_stats function with a sample meal ID
    meal_id = 1
    update_meal_stats(meal_id, "win")

    # Normalize the expected SQL query
    expected_query = normalize_whitespace("""
        UPDATE meals SET SET battles = battles + 1 AND wins = wins + 1 WHERE id = ?
    """)

    # Ensure the SQL query was executed correctly
    actual_query = normalize_whitespace(mock_cursor.execute.call_args_list[1][0][0])

    # Assert that the SQL query was correct
    assert actual_query == expected_query, "The SQL query did not match the expected structure."

    # Extract the arguments used in the SQL call
    actual_arguments = mock_cursor.execute.call_args_list[1][0][1]

    # Assert that the SQL query was executed with the correct arguments (meals ID)
    expected_arguments = (meal_id,)
    assert actual_arguments == expected_arguments, f"The SQL query arguments did not match. Expected {expected_arguments}, got {actual_arguments}."

def test_update_meal_stats_loss(mock_cursor):
    """Test updating battle stats of a meal after a loss."""

    # Simulate that the meal exists and is not deleted (id = 1)
    mock_cursor.fetchone.return_value = [False]

    # Call the update_meal_stats function with a sample meal ID
    meal_id = 1
    update_meal_stats(meal_id, "win")

    # Normalize the expected SQL query
    expected_query = normalize_whitespace("""
        UPDATE meals SET SET battles = battles + 1 WHERE id = ?
    """)

    # Ensure the SQL query was executed correctly
    actual_query = normalize_whitespace(mock_cursor.execute.call_args_list[1][0][0])

    # Assert that the SQL query was correct
    assert actual_query == expected_query, "The SQL query did not match the expected structure."

    # Extract the arguments used in the SQL call
    actual_arguments = mock_cursor.execute.call_args_list[1][0][1]

    # Assert that the SQL query was executed with the correct arguments (meal ID)
    expected_arguments = (meal_id,)
    assert actual_arguments == expected_arguments, f"The SQL query arguments did not match. Expected {expected_arguments}, got {actual_arguments}."

def test_update_meal_stats_deleted_meal(mock_cursor):
    """Test error when trying to update battle statistics for a deleted meal."""

    # Simulate that the meal exists but is marked as deleted (id = 1)
    mock_cursor.fetchone.return_value = [True]

    # Expect a ValueError when attempting to update a deleted meal
    with pytest.raises(ValueError, match="Meal with ID 1 has been deleted"):
        update_meal_stats(1)

    # Ensure that no SQL query for updating meal stats was executed
    mock_cursor.execute.assert_called_once_with("SELECT deleted FROM meals WHERE id = ?", (1,))

def test_update_meal_stats_bad_id(mock_cursor):
    """Test updating the battle statistics of a meal when ID is invalid."""

    # Simulate that no meal exists for the given ID
    mock_cursor.fetchone.return_value = None

    # Expect a ValueError when the meal is not found
    with pytest.raises(ValueError, match="Meal with ID 999 not found"):
        update_meal_stats(999)