from typing import Any, Dict, List, Optional, Type, TypeVar, Generic
from sqlalchemy.orm import (scoped_session, InstrumentedAttribute)
from sqlalchemy.ext.declarative import DeclarativeMeta
from sqlalchemy import Column, and_

T = TypeVar("T", bound=DeclarativeMeta)

class BaseRepository(Generic[T]):
    def __init__(self, session: scoped_session, model: Type[T]):
        self.session = session
        self.model = model

    def exists_by(self, **kwargs) -> bool:
        """
        指定したカラムと値の組み合わせで存在チェック
        例: exists_by(email="test@example.com")
        """
        return self.session.query(
            self.session.query(self.model).filter_by(**kwargs).exists()
        ).scalar()
    
    # def find_all(self, **kwargs) -> list[T]:
    #     """
    #     条件指定があれば filter_by、なければ全件取得。
    #     """
    #     query = self.session.query(self.model)
    #     if kwargs:
    #         query = query.filter_by(**kwargs)
    #     return query.all()

    def find_all(self, **filters) -> list[T]:
        """
        filters 例:
        - {"name": "test"}             完全一致
        - {"name__ne": "test"}         not
        - {"name__like": "abc"}        部分一致
        - {"name__startswith": "abc"}  前方一致
        - {"age__gte": 20}             範囲
        - {"age__lte": 50}
        """
        query = self.session.query(self.model)

        conditions = []
        for key, value in filters.items():
            if "__" in key:
                attr_name, op = key.split("__", 1)
            else:
                attr_name, op = key, "eq"

            column: InstrumentedAttribute = getattr(self.model, attr_name, None)
            if not column:
                continue  # モデルにない属性はスキップ or raise Exception

            # オペレーター処理
            if op == "eq":
                conditions.append(column == value)
            if op == "ne":
                conditions.append(column != value)
            elif op == "like":
                conditions.append(column.like(f"%{value}%"))
            elif op == "startswith":
                conditions.append(column.ilike(f"{value}%"))
            elif op == "gte":
                conditions.append(column >= value)
            elif op == "lte":
                conditions.append(column <= value)
            elif op == "in":
                if isinstance(value, list):
                    conditions.append(column.in_(value))

        if conditions:
            query = query.filter(*conditions)

        return query.all()
    
    def find_by_id(self, id: Any) -> Optional[T]:
        return self.session.query(self.model).get(id)

    def find_one_by(self, **kwargs) -> Optional[T]:
        return self.session.query(self.model).filter_by(**kwargs).first()

    def find_all_by(self, **kwargs) -> List[T]:
        return self.session.query(self.model).filter_by(**kwargs).all()

    def insert(self, data: Dict[str, Any]) -> T:
        instance = self.model(**data)
        self.session.add(instance)
        self.session.commit()
        self.session.refresh(instance)
        return instance

    def insert(self, data: Dict[str, Any]) -> T:
        instance = self.model(**data)
        self.session.add(instance)
        self.session.commit()
        self.session.refresh(instance)
        return instance
    
    def insert_entity(self, entity: T) -> T:
        self.session.add(entity)
        self.session.commit()
        self.session.refresh(entity)
        return entity
    
    def insert_many(self, entities: list[T]) -> list[T]:
        self.session.add_all(entities)
        self.session.commit()
        for entity in entities:
            self.session.refresh(entity)
        return entities

    def update(self, instance: T, data: Dict[str, Any]) -> T:
        for key, value in data.items():
            setattr(instance, key, value)
        self.session.commit()
        self.session.refresh(instance)
        return instance

    def delete(self, instance: T) -> None:
        self.session.delete(instance)
        self.session.commit()
    
    def delete_by_conditions(self, conditions: dict) -> int:
        """
        条件を可変で指定してまとめて削除する。

        Args:
            conditions (dict): {カラム名: 値, …}

        Returns:
            int: 削除した件数
        """
        query = self.session.query(self.model)

        if conditions:
            filters = [getattr(self.model, key) == value for key, value in conditions.items()]
            query = query.filter(and_(*filters))

        deleted_count = query.delete(synchronize_session=False)
        self.session.commit()
        return deleted_count

# user_repo = BaseRepository(session=db.session, model=MUser)

# # id で存在チェック
# user_repo.exists_by(id=1)

# # email で存在チェック
# user_repo.exists_by(email="test@example.com")

# # 複数条件でもOK
# user_repo.exists_by(email="a@example.com", is_active=True)