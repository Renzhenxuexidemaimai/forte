# Copyright 2019 The Forte Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
Defines the basic data structures and interfaces for the Forte data
representation system.
"""

from abc import abstractmethod, ABC
from typing import Iterable, Optional, Set, Type, Hashable, TypeVar, Generic

import numpy as np

from forte.data.container import ContainerType

__all__ = [
    "Entry",
    "BaseLink",
    "BaseGroup",
    "LinkType",
    "GroupType",
    "EntryType",
]


class Entry(Generic[ContainerType]):
    r"""The base class inherited by all NLP entries. This is the main data type
    for all in-text NLP analysis results. The main sub-types are
    ``Annotation``, ``Link`` and ``Group``.

    An :class:`forte.data.ontology.top.Annotation` object represents a
    span in text.

    A :class:`forte.data.ontology.top.Link` object represents a binary
    link relation between two entries.

    A :class:`forte.data.ontology.top.Group` object represents a
    collection of multiple entries.

    There will be some associated attributes for each entry, which can be
    set via :meth:`set_fields` and retrieved via :meth:`get_field`.

    Attributes:
        self.embedding: The embedding vectors (numpy array of floats) of this
            entry.

    Args:
        pack: Each entry should be associated with one pack upon creation.
    """

    def __init__(self, pack: ContainerType):
        super().__init__()

        self._tid: int = pack.get_next_id()

        self._embedding: np.ndarray = np.empty(0)

        # The Entry should have a reference to the data pack, and the data pack
        # need to store the entries. In order to resolve the cyclic references,
        # we create a generic class EntryContainer to be the place holder of
        # the actual. Whether this entry can be added to the pack is delegated
        # to be checked by the pack.
        self.__pack: ContainerType = pack
        self.__field_modified: Set[str] = set()
        pack.validate(self)

        self.record_creation()

    def record_creation(self):
        self.__pack.add_entry_creation_record(self._tid)

    def reset(self):
        """
        Reset the entry to the empty state.

        Returns:

        """
        # TODO: do we need to record this reset action as an edit?
        self.__init__(self.__pack)

    def __getstate__(self):
        r"""In serialization, the pack is not serialize, and it will be set
        by the container.

        This also implies that it is not advised to serialize an entry on its
        own, without the ``Container`` as the context, there is little semantics
        remained in an entry.
        """
        state = self.__dict__.copy()
        # During serialization, convert the numpy array as a list.
        state["_embedding"] = self._embedding.tolist()
        state.pop('_Entry__pack')
        state.pop('_Entry__field_modified')
        return state

    def __setstate__(self, state):
        # Recover the internal __field_modified dict for the entry.
        # NOTE: the __pack will be set via set_pack from the Pack side.
        self.__dict__['_Entry__field_modified'] = set()
        # During de-serialization, convert the list back to numpy array.
        state["_embedding"] = np.array(state["_embedding"])
        self.__dict__.update(state)

    # using property decorator
    # a getter function for self._embedding
    @property
    def embedding(self):
        r"""Get the embedding vectors (numpy array of floats) of the entry.
        """
        return self._embedding

    # a setter function for self._embedding
    @embedding.setter
    def embedding(self, embed):
        r"""Set the embedding vectors of the entry.

        Args:
            embed: The embedding vectors which can be numpy array of floats or
                list of floats.
        """
        self._embedding = np.array(embed)

    @property
    def tid(self) -> int:
        """
        Get the id of this entry.

        Returns:

        """
        return self._tid

    @property
    def pack(self) -> ContainerType:
        return self.__pack

    @property
    def pack_id(self) -> int:
        """
        Get the id of the pack that contains this entry.

        Returns:

        """
        return self.__pack.meta.pack_id  # type: ignore

    def set_pack(self, pack: ContainerType):
        self.__pack = pack

    def set_fields(self, **kwargs):
        r"""Set the entry fields from the kwargs.

        Args:
            **kwargs: A set of key word arguments used to set the value. A key
            must be correspond to a field name of this entry, and a value must
            match the field's type.
        """
        for field_name, field_value in kwargs.items():
            if field_name in vars(self):
                # NOTE: hasattr does not work here because it check both
                #  functions and attributes. We are only interested to see if
                #  the attributes are there.
                #  For example, if we use hasattr, is will return True for
                #  the setter and getter of the attribute name.

                # if hasattr(self, field_name):
                setattr(self, field_name, field_value)
            else:
                raise AttributeError(
                    f"The entry type [{self.__class__}] does not have an "
                    f"attribute: '{field_name}'.")

            # We add the record to the system.
            self.__pack.add_field_record(self.tid, field_name)

    def get_field(self, field_name):
        return getattr(self, field_name)

    def __eq__(self, other):
        r"""The eq function for :class:`Entry` objects.
        To be implemented in each subclass.
        """
        if other is None:
            return False

        return (type(self), self._tid) == (type(other), other.tid)

    def __hash__(self) -> int:
        r"""The hash function for :class:`Entry` objects.
        To be implemented in each subclass.
        """
        return hash((type(self), self._tid))

    @property
    def index_key(self) -> Hashable:
        return self._tid


EntryType = TypeVar("EntryType", bound=Entry)


class BaseLink(Entry, ABC):
    def __init__(
            self,
            pack: ContainerType,
            parent: Optional[Entry] = None,
            child: Optional[Entry] = None
    ):
        super().__init__(pack)

        if parent is not None:
            self.set_parent(parent)
        if child is not None:
            self.set_child(child)

    @abstractmethod
    def set_parent(self, parent: Entry):
        r"""This will set the `parent` of the current instance with given Entry
        The parent is saved internally by its pack specific index key.

        Args:
            parent: The parent entry.
        """
        raise NotImplementedError

    @abstractmethod
    def set_child(self, child: Entry):
        r"""This will set the `child` of the current instance with given Entry
        The child is saved internally by its pack specific index key.

        Args:
            child: The child entry
        """
        raise NotImplementedError

    @abstractmethod
    def get_parent(self) -> Entry:
        r"""Get the parent entry of the link.

        Returns:
             An instance of :class:`Entry` that is the child of the link
             from the given :class:`DataPack`.
        """
        raise NotImplementedError

    @abstractmethod
    def get_child(self) -> Entry:
        r"""Get the child entry of the link.

        Returns:
             An instance of :class:`Entry` that is the child of the link
             from the given :class:`DataPack`.
        """
        raise NotImplementedError

    def __eq__(self, other):
        if other is None:
            return False
        return (type(self), self.get_parent(), self.get_child()) == \
               (type(other), other.get_parent(), other.get_child())

    def __hash__(self):
        return hash((type(self), self.get_parent(), self.get_child()))

    @property
    def index_key(self) -> int:
        return self.tid


class BaseGroup(Entry, Generic[EntryType]):
    r"""Group is an entry that represent a group of other entries. For example,
    a "coreference group" is a group of coreferential entities. Each group will
    store a set of members, no duplications allowed.

    This is the :class:`BaseGroup` interface. Specific member constraints are
    defined in the inherited classes.
    """
    MemberType: Type[EntryType]

    def __init__(
            self,
            pack: ContainerType,
            members: Optional[Set[EntryType]] = None,
    ):
        super().__init__(pack)

        # Store the group member's id.
        self._members: Set[int] = set()
        if members is not None:
            self.add_members(members)

    def add_member(self, member: EntryType):
        r"""Add one entry to the group.

        Args:
            member: One member to be added to the group.
        """
        self.add_members([member])

    def add_members(self, members: Iterable[EntryType]):
        r"""Add members to the group.

        Args:
            members: An iterator of members to be added to the group.
        """
        for member in members:
            if not isinstance(member, self.MemberType):
                raise TypeError(
                    f"The members of {type(self)} should be "
                    f"instances of {self.MemberType}, but got {type(member)}")

            self._members.add(member.tid)

    @property
    def members(self):
        r"""A list of member tids. To get the member objects, call
        :meth:`get_members` instead.
        """
        return self._members

    def __hash__(self):
        r"""The hash function of :class:`Group`.

        Users can define their own hash function by themselves but this must
        be consistent to :meth:`eq`.
        """
        return hash((type(self), tuple(self.members)))

    def __eq__(self, other):
        r"""The eq function of :class:`Group`. By default, :class:`Group`
        objects are regarded as the same if they have the same type, members,
        and are generated by the same component.

        Users can define their own eq function by themselves but this must
        be consistent to :meth:`hash`.
        """
        if other is None:
            return False
        return (type(self), self.members) == (type(other), other.members)

    def get_members(self):
        r"""Get the member entries in the group.

        Returns:
             An set of instances of :class:`Entry` that are the members of the
             group.
        """
        if self.pack is None:
            raise ValueError(f"Cannot get members because group is not "
                             f"attached to any data pack.")
        member_entries = set()
        for m in self.members:
            member_entries.add(self.pack.get_entry(m))
        return member_entries

    @property
    def index_key(self) -> int:
        return self.tid


GroupType = TypeVar("GroupType", bound=BaseGroup)
LinkType = TypeVar('LinkType', bound=BaseLink)
