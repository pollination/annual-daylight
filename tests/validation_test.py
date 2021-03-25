from pollination.annual_daylight.entry import AnnualDaylightEntryPoint
from queenbee.recipe.dag import DAG


def test_annual_daylight():
    recipe = AnnualDaylightEntryPoint().queenbee
    assert recipe.name == 'annual-daylight-entry-point'
    assert isinstance(recipe, DAG)
