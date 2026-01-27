from typing import List, Type, Union

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from movies.models import Genre, Star, Director


async def get_or_create_related(
    model: Type[Union[Genre, Star, Director]],
    names: List[str],
    db: AsyncSession
) -> List[Union[Genre | Star | Director]]:
    """
    Fetches related items by name from the DB and creates new ones if needed.
    
    Args:
        model: Type[Union[Genre, Star, Director]] - The type of related item
        names: List[str] - Names to fetch or create
        db: AsyncSession - The DB session to use
    
    Returns:
        List[Union[Genre | Star | Director]] - A list of related items
    """
    if not names: return []

    # 1. Remove duplicates from input list to prevent redundant processing
    unique_names = list(set(name.strip() for name in names if name))

    # 2. Fetch all that exist in one query
    stmt = select(model).where(model.name.in_(unique_names))
    result = await db.execute(stmt)
    existing_items = list(result.scalars().all())
    
    # Map by name for quick lookup
    existing_map = {item.name: item for item in existing_items}

    # 3. Identify and Create missing items
    final_items = []
    for name in unique_names:
        if name in existing_map:
            final_items.append(existing_map[name])
        else:
            # This is a truly new item
            new_item = model(name=name)
            db.add(new_item)
            final_items.append(new_item)
    
    # 4. Optional: Flush here to catch sequence or unique issues immediately
    # If there is at least one new object created, flush
    if any(item not in existing_items for item in final_items):
        await db.flush()

    return final_items
