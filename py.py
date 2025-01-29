import os
import requests
from requests.auth import HTTPBasicAuth
from functools import lru_cache
from typing import Dict, List, Optional, TypedDict, Union, Literal
from dotenv import load_dotenv
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal

# Load environment variables
load_dotenv()

class ImageInfo(TypedDict):
    """Type definition for food images based on API documentation."""
    image_url: str
    image_type: Literal["Standard", "Isolated"]

class ServingInfo(TypedDict, total=False):
    """Type definition for serving information matching API documentation."""
    serving_id: str
    serving_description: str
    serving_url: str
    metric_serving_amount: Optional[Decimal]  # Changed to Optional as per docs
    metric_serving_unit: Optional[Literal["g", "ml", "oz"]]  # Made Optional
    number_of_units: Optional[Decimal]  # Made Optional
    measurement_description: str
    is_default: Optional[int]  # Made Optional as it's Premier Exclusive
    calories: Optional[Decimal]
    carbohydrate: Optional[Decimal]
    protein: Optional[Decimal]
    fat: Optional[Decimal]
    saturated_fat: Optional[Decimal]
    polyunsaturated_fat: Optional[Decimal]
    monounsaturated_fat: Optional[Decimal]
    trans_fat: Optional[Decimal]
    cholesterol: Optional[Decimal]
    sodium: Optional[Decimal]
    potassium: Optional[Decimal]
    fiber: Optional[Decimal]
    sugar: Optional[Decimal]
    added_sugars: Optional[Decimal]
    vitamin_d: Optional[Decimal]
    vitamin_a: Optional[Decimal]
    vitamin_c: Optional[Decimal]
    calcium: Optional[Decimal]
    iron: Optional[Decimal]

class AllergenInfo(TypedDict):
    """Type definition for allergen information based on API documentation."""
    id: str
    name: Literal[
        "Egg", "Fish", "Gluten", "Lactose", "Milk",
        "Nuts", "Peanuts", "Sesame", "Shellfish", "Soy"
    ]
    value: Literal[-1, 0, 1]  # -1: Unknown, 0: False, 1: True

class PreferenceInfo(TypedDict):
    """Type definition for dietary preference information based on API documentation."""
    id: str
    name: Literal["Vegan", "Vegetarian"]
    value: Literal[-1, 0, 1]  # -1: Unknown, 0: False, 1: True

@dataclass
class FoodItem:
    """Data class for food items matching API documentation structure."""
    food_id: str
    food_name: str
    brand_name: Optional[str]  # Optional for Generic foods
    food_type: Literal["Brand", "Generic"]
    food_url: str
    food_sub_categories: Optional[List[str]]  # Made Optional as it's Premier Exclusive
    images: List[ImageInfo]
    servings: List[ServingInfo]
    allergens: Dict[str, int]  # name -> value mapping
    preferences: Dict[str, int]  # name -> value mapping

class FatSecretError(Exception):
    """Custom exception for FatSecret API errors."""
    ERROR_MESSAGES = {
        2: "Missing required OAuth parameter",
        3: "Unsupported OAuth parameter",
        4: "Invalid signature method",
        5: "Invalid consumer key",
        6: "Invalid/expired timestamp",
        7: "Invalid/used nonce",
        8: "Invalid signature",
        9: "Invalid access token",
        13: "Invalid OAuth 2.0 token",
        14: "Missing OAuth 2.0 scope",
        107: "Parameter value out of range"
    }

    def __init__(self, error_code: int, details: str = None):
        self.error_code = error_code
        self.details = details
        message = f"{self.ERROR_MESSAGES.get(error_code, 'Unknown error')}"
        if details:
            message += f": {details}"
        super().__init__(message)

class FatSecretAPI:
    """API client for FatSecret with documentation-based implementation."""
    
    def __init__(self):
        """Initialize the API client using environment variables."""
        self.client_id = os.getenv('FATSECRET_CLIENT_ID')
        self.client_secret = os.getenv('FATSECRET_CLIENT_SECRET')
        
        if not self.client_id or not self.client_secret:
            raise ValueError(
                "Missing API credentials. Please set FATSECRET_CLIENT_ID and "
                "FATSECRET_CLIENT_SECRET environment variables."
            )
        
        self._token = None
        self._token_expiry = None

    def _decimal_or_none(self, value: Union[str, None]) -> Optional[Decimal]:
        """Convert string to Decimal or return None for invalid/missing values."""
        try:
            return Decimal(value) if value is not None else None
        except (TypeError, ValueError):
            return None

    def get_access_token(self) -> str:
        """Fetch and cache the access token with expiration handling."""
        if self._token and self._token_expiry and datetime.now() < self._token_expiry:
            return self._token

        url = "https://oauth.fatsecret.com/connect/token"
        payload = {"grant_type": "client_credentials", "scope": "basic"}
        
        try:
            response = requests.post(
                url,
                auth=HTTPBasicAuth(self.client_id, self.client_secret),
                data=payload
            )
            response.raise_for_status()
            data = response.json()
            
            self._token = data.get("access_token")
            self._token_expiry = datetime.now() + timedelta(hours=23)
            
            return self._token
        except requests.exceptions.RequestException as e:
            raise FatSecretError(13, str(e))

    def _parse_serving(self, serving: Dict) -> ServingInfo:
        """Parse a single serving entry according to API documentation."""
        return {
            'serving_id': serving.get('serving_id', ''),
            'serving_description': serving.get('serving_description', ''),
            'serving_url': serving.get('serving_url', ''),
            'metric_serving_amount': self._decimal_or_none(serving.get('metric_serving_amount')),
            'metric_serving_unit': serving.get('metric_serving_unit'),
            'number_of_units': self._decimal_or_none(serving.get('number_of_units')),
            'measurement_description': serving.get('measurement_description', ''),
            'is_default': int(serving.get('is_default', 0)) if 'is_default' in serving else None,
            'calories': self._decimal_or_none(serving.get('calories')),
            'carbohydrate': self._decimal_or_none(serving.get('carbohydrate')),
            'protein': self._decimal_or_none(serving.get('protein')),
            'fat': self._decimal_or_none(serving.get('fat')),
            'saturated_fat': self._decimal_or_none(serving.get('saturated_fat')),
            'polyunsaturated_fat': self._decimal_or_none(serving.get('polyunsaturated_fat')),
            'monounsaturated_fat': self._decimal_or_none(serving.get('monounsaturated_fat')),
            'trans_fat': self._decimal_or_none(serving.get('trans_fat')),
            'cholesterol': self._decimal_or_none(serving.get('cholesterol')),
            'sodium': self._decimal_or_none(serving.get('sodium')),
            'potassium': self._decimal_or_none(serving.get('potassium')),
            'fiber': self._decimal_or_none(serving.get('fiber')),
            'sugar': self._decimal_or_none(serving.get('sugar')),
            'added_sugars': self._decimal_or_none(serving.get('added_sugars')),
            'vitamin_d': self._decimal_or_none(serving.get('vitamin_d')),
            'vitamin_a': self._decimal_or_none(serving.get('vitamin_a')),
            'vitamin_c': self._decimal_or_none(serving.get('vitamin_c')),
            'calcium': self._decimal_or_none(serving.get('calcium')),
            'iron': self._decimal_or_none(serving.get('iron'))
        }

    def _parse_food_item(self, food: Dict) -> FoodItem:
        """Parse a food item according to API documentation structure."""
        # Parse allergens with proper type handling
        allergens = {}
        allergens_data = food.get('food_attributes', {}).get('allergens', {}).get('allergen', [])
        if not isinstance(allergens_data, list):
            allergens_data = [allergens_data] if allergens_data else []
        for allergen in allergens_data:
            allergens[allergen['name']] = int(allergen['value'])

        # Parse preferences with proper type handling
        preferences = {}
        preferences_data = food.get('food_attributes', {}).get('preferences', {}).get('preference', [])
        if not isinstance(preferences_data, list):
            preferences_data = [preferences_data] if preferences_data else []
        for pref in preferences_data:
            preferences[pref['name']] = int(pref['value'])

        # Parse servings
        servings_data = food.get('servings', {}).get('serving', [])
        if not isinstance(servings_data, list):
            servings_data = [servings_data] if servings_data else []
        servings = [self._parse_serving(serving) for serving in servings_data]

        # Parse images
        images = []
        images_data = food.get('food_images', {}).get('food_image', [])
        if not isinstance(images_data, list):
            images_data = [images_data] if images_data else []
        for image in images_data:
            images.append({
                'image_url': image.get('image_url', ''),
                'image_type': image.get('image_type', 'Standard')
            })

        # Parse sub-categories (Premier Exclusive feature)
        sub_categories = food.get('food_sub_categories', {}).get('food_sub_category', [])
        if not isinstance(sub_categories, list):
            sub_categories = [sub_categories] if sub_categories else []

        return FoodItem(
            food_id=food.get('food_id', ''),
            food_name=food.get('food_name', ''),
            brand_name=food.get('brand_name'),
            food_type=food.get('food_type', 'Generic'),
            food_url=food.get('food_url', ''),
            food_sub_categories=sub_categories if sub_categories else None,
            images=images,
            servings=servings,
            allergens=allergens,
            preferences=preferences
        )

    def search_food(
        self,
        query: str,
        max_results: int = 20,
        page_number: int = 0
    ) -> List[FoodItem]:
        if not 1 <= max_results <= 50:
            raise FatSecretError(107, "max_results must be between 1 and 50")
        
        access_token = self.get_access_token()
        url = "https://platform.fatsecret.com/rest/server.api"
        
        params = {
            "method": "foods.search",
            "format": "json",
            "search_expression": query,
            "max_results": max_results,
            "page_number": page_number
        }
        
        headers = {"Authorization": f"Bearer {access_token}"}
        
        try:
            response = requests.get(url, params=params, headers=headers)
            response.raise_for_status()
            data = response.json()
            
            search_results = data.get('foods_search', {})
            total_results = int(search_results.get('total_results', 0))
            
            if total_results == 0:
                return []
                
            foods_data = search_results.get('results', {}).get('food', [])
            if not isinstance(foods_data, list):
                foods_data = [foods_data] if foods_data else []
                
            return [self._parse_food_item(food) for food in foods_data]
            
        except requests.exceptions.RequestException as e:
            raise FatSecretError(13, str(e))

def format_nutrient(value: Optional[Decimal], unit: str) -> str:
    """Format nutrient value with unit, handling None values."""
    if value is None:
        return "Not available"
    return f"{value} {unit}"

def main():
    """Example usage of the API client."""
    try:
        client = FatSecretAPI()
        
        query = input("Enter food to search: ")
        max_results = int(input("Enter number of results (1-50): "))
        page_number = int(input("Enter page number: "))
        
        foods = client.search_food(query, max_results, page_number)
        
        for food in foods:
            print(f"\n{'='*60}")
            print(f"Food: {food.food_name}")
            if food.brand_name:
                print(f"Brand: {food.brand_name}")
            print(f"Type: {food.food_type}")
            print(f"URL: {food.food_url}")
            
            if food.food_sub_categories:
                print("\nCategories:", ", ".join(food.food_sub_categories))
            
            if food.images:
                print("\nImages:")
                for img in food.images:
                    print(f"  {img['image_type']}: {img['image_url']}")
            
            if food.allergens:
                print("\nAllergens:")
                for allergen, value in food.allergens.items():
                    status = "Unknown" if value == -1 else ("Yes" if value == 1 else "No")
                    print(f"  {allergen}: {status}")
            
            if food.preferences:
                print("\nDietary Info:")
                for pref, value in food.preferences.items():
                    status = "Unknown" if value == -1 else ("Yes" if value == 1 else "No")
                    print(f"  {pref}: {status}")
            
            if food.servings:
                print("\nServings:")
                for serving in food.servings:
                    print(f"\n  {serving['serving_description']}")
                    if serving.get('metric_serving_amount') and serving.get('metric_serving_unit'):
                        print(f"  Amount: {serving['metric_serving_amount']} {serving['metric_serving_unit']}")
                    
                    # Display serving measurements
                    if serving.get('number_of_units'):
                        print(f"  Units: {serving['number_of_units']}")
                    if serving.get('measurement_description'):
                        print(f"  Measurement: {serving['measurement_description']}")
                    if serving.get('is_default'):
                        print("  (Default Serving)")
                    
                    # Basic nutritional information
                    print(f"  Calories: {format_nutrient(serving.get('calories'), 'kcal')}")
                    print(f"  Protein: {format_nutrient(serving.get('protein'), 'g')}")
                    print(f"  Carbohydrates: {format_nutrient(serving.get('carbohydrate'), 'g')}")
                    print(f"  Fat: {format_nutrient(serving.get('fat'), 'g')}")
                    
                    # Detailed fat breakdown
                    if serving.get('saturated_fat'):
                        print(f"  Saturated Fat: {format_nutrient(serving['saturated_fat'], 'g')}")
                    if serving.get('polyunsaturated_fat'):
                        print(f"  Polyunsaturated Fat: {format_nutrient(serving['polyunsaturated_fat'], 'g')}")
                    if serving.get('monounsaturated_fat'):
                        print(f"  Monounsaturated Fat: {format_nutrient(serving['monounsaturated_fat'], 'g')}")
                    if serving.get('trans_fat'):
                        print(f"  Trans Fat: {format_nutrient(serving['trans_fat'], 'g')}")
                    
                    # Cholesterol and minerals
                    if serving.get('cholesterol'):
                        print(f"  Cholesterol: {format_nutrient(serving['cholesterol'], 'mg')}")
                    if serving.get('sodium'):
                        print(f"  Sodium: {format_nutrient(serving['sodium'], 'mg')}")
                    if serving.get('potassium'):
                        print(f"  Potassium: {format_nutrient(serving['potassium'], 'mg')}")
                    
                    # Carbohydrate details
                    if serving.get('fiber'):
                        print(f"  Fiber: {format_nutrient(serving['fiber'], 'g')}")
                    if serving.get('sugar'):
                        print(f"  Sugar: {format_nutrient(serving['sugar'], 'g')}")
                    if serving.get('added_sugars'):
                        print(f"  Added Sugars: {format_nutrient(serving['added_sugars'], 'g')}")
                    
                    # Vitamins and minerals
                    if serving.get('vitamin_d'):
                        print(f"  Vitamin D: {format_nutrient(serving['vitamin_d'], 'µg')}")
                    if serving.get('vitamin_a'):
                        print(f"  Vitamin A: {format_nutrient(serving['vitamin_a'], 'µg')}")
                    if serving.get('vitamin_c'):
                        print(f"  Vitamin C: {format_nutrient(serving['vitamin_c'], 'mg')}")
                    if serving.get('calcium'):
                        print(f"  Calcium: {format_nutrient(serving['calcium'], 'mg')}")
                    if serving.get('iron'):
                        print(f"  Iron: {format_nutrient(serving['iron'], 'mg')}")
    
    except ValueError as e:
        print(f"Error: {e}")
    except FatSecretError as e:
        print(f"API Error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")

if __name__ == "__main__":
    main()