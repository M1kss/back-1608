__all__ = ['PaginationMixin', 'is_field', 'is_relationship']

import re

from sqlalchemy.sql.elements import True_
from sqlalchemy.inspection import inspect
from sqlalchemy import desc
from flask_sqlalchemy import Model


def is_field(entity_cls, attr):
    """
    Shows if attribute attr represents field to which filtering can be applied.
    Raises an exception if arguments has wrong type.
    :param type entity_cls: entity class
    :param str attr: attribute name
    :return bool:
    """
    if attr == '__mapper__':
        return False
    mapper = inspect(entity_cls)
    return attr in mapper.all_orm_descriptors and attr not in mapper.relationships


def is_relationship(entity_cls, attr):
    """
    Shows if attribute attr represents relationship to any other entity.
    Raises an exception if arguments has wrong type.
    :param type entity_cls: entity class
    :param str attr: relationship name
    :return bool:
    """
    return attr in inspect(entity_cls).relationships


class PaginationMixin:
    BaseEntity = None
    used_release = None

    def __init__(self, base_entity_cls=None):
        """
        Создает объект класса PaginationMixin с установленным значением базовой сущности.
        Созданный таким образом объект можно использовать для доступа к функции paginate без создания подклассов.
        """
        if base_entity_cls is not None:
            self.BaseEntity = base_entity_cls

    def _check_entity_type(self):
        if not issubclass(self.BaseEntity, Model):
            raise ValueError('PaginationMixin requires set BaseEntity')

    def parse_order_clauses(self, sorting_str):
        """
        Преобразовывает строку с критериями сортировки, разделенными ::, в список критериев sqlalchemy.
        Выражения, не имеющие вид "[-]column" неизвестными значениями для column, игнорируются.
        :param sorting_str:
        :return:
        """
        if not sorting_str:
            return []
        order_clauses = []
        for criterion in sorting_str.strip().split('::'):
            descending = False
            if criterion.startswith('-'):
                descending = True
                criterion = criterion[1:]

            if is_field(self.BaseEntity, criterion):
                variable = getattr(self.BaseEntity, criterion)
                order_clauses.append(variable.desc() if descending else variable)

        return order_clauses

    def paginate(self, args, extra_filters=(), default_order_clauses=(), mode='all'):
        """
        Returns list of self.BaseEntity objects taking into account the parameters passed in args.
        :param args: dictionary with the following keys:
                     size - number of objects should be returned. Interpreted as capacity of one page.
                            No limitations if size is not provided or equals to zero.
                     offset - number of objects should be skipped before pagination.
                     page - number of page to return. Ignored, if size is not positive integer.
                     order_by - string specifying order of objects in the selection. See `parse_order_clauses` method.
        :param extra_filters: list of additional filters in sqlalchemy format, like 'User.id == 4'.
                              Use this parameter to restrict access to objects without changing filtering string.
        :param default_order_clauses: list of additional order by clauses in sqlalchemy format, like 'User.id'.
                              Use this parameter to apply sorting by default.
        :param mode: 'all' or 'query' - whether to return a list of items or sqlalchemy query instance
        :return: list of BaseEntity objects.
        """
        self._check_entity_type()

        page = args.get('page')
        size = args.get('size')
        offset = args.get('offset')
        sorting_str = args.get('order_by')

        order_clauses = self.parse_order_clauses(sorting_str)

        query = self.BaseEntity.query
        query = query.filter(*extra_filters)

        if order_clauses:
            query = query.order_by(*order_clauses)
        else:
            query = query.order_by(*default_order_clauses)

        if size:
            start = offset + size * (page - 1)
            query = query.slice(start, start + size)
        elif offset:
            query = query.offset(offset)

        if mode == 'query':
            return query
        elif mode == 'all':
            return query.all()
        else:
            raise ValueError(mode)

    def items_count(self, extra_filters=()):
        """
        Return amount of self.BaseEntity objects in the database satisfying given filters.
        Supports both filters_str (see `parse_filters` method) and prepared sqlalchemy conditions.
        :param extra_filters: list of additional filters in sqlalchemy format, like 'User.id == 4'.
                              Use this parameter to restrict access to objects without changing filtering string.
        :return int: number of BaseEntity objects.
        """
        self._check_entity_type()
        return self.BaseEntity.query.filter(*extra_filters).count()
