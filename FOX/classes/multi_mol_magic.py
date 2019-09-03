"""
FOX.classes.multi_mol_magic
===========================

A Module for setting up the magic methods and properties of the :class:`.MultiMolecule` class.

Index
-----
.. currentmodule:: FOX.classes.multi_mol_magic
.. autosummary::
    _MultiMolecule

API
---
.. autoclass:: FOX.classes.multi_mol_magic._MultiMolecule
    :members:
    :private-members:
    :special-members:

"""

from __future__ import annotations

import copy as pycopy
import textwrap
import itertools
from collections import abc
from typing import (Dict, Optional, List, Any, Callable, Union, Sequence)

import numpy as np

from scm.plams import PeriodicTable
from scm.plams.core.errors import PTError
from scm.plams.core.settings import Settings

from .multi_mol_repr import MultiMolRepr
from ..functions.utils import get_nested_element

__all__: List[str] = []

_prop_dict: Dict[str, Callable] = {
    'symbol': lambda x: x,
    'radius': PeriodicTable.get_radius,
    'atnum': PeriodicTable.get_atomic_number,
    'mass': PeriodicTable.get_mass,
    'connectors': PeriodicTable.get_connectors
}

_none_dict: Dict[str, Union[str, int, float]] = {
    'symbol': '', 'radius': -1, 'atnum': -1, 'mass': np.nan, 'connectors': -1
}

_shape_warning: str = ("ValueWarning: The '{}' argument expects a 'm*n*k' sequence. "
                       "The following shape was observed: '{}'")

_dtype_warning: str = ("TypeWarning: The '{}' argument expects a sequence consisting of floats. "
                       "The following element type was observed: '{}'")

_type_error: str = ("The '{}' argument expects a sequence. "
                    "The following type was observed: '{}'")


class _MultiMolecule(np.ndarray):
    """Private superclass of :class:`.MultiMolecule`.

    Handles all magic methods and @property decorated methods.
    """

    def __new__(cls, coords: np.ndarray,
                atoms: Optional[Dict[str, List[int]]] = None,
                bonds: Optional[np.ndarray] = None,
                properties: Optional[Dict[str, Any]] = None) -> _MultiMolecule:
        """Create and return a new object."""
        obj = _MultiMolecule._sanitize_coords(coords).view(cls)

        # Set attributes
        obj.atoms = _MultiMolecule._sanitize_atoms(atoms)
        obj.bonds = _MultiMolecule._sanitize_bonds(bonds)
        obj.properties = _MultiMolecule._sanitize_properties(properties)
        obj._ndrepr = MultiMolRepr()
        return obj

    def __array_finalize__(self, obj: _MultiMolecule) -> None:
        """Finalize the array creation."""
        if obj is None:
            return

        self.atoms = getattr(obj, 'atoms', None)
        self.bonds = getattr(obj, 'bonds', None)
        self.properties = getattr(obj, 'properties', None)
        self._ndrepr = getattr(obj, '_ndrepr', None)

    @staticmethod
    def _is_array_like(value: Any) -> bool:
        """Check if value is array-like."""
        ret = (
            isinstance(value, abc.Sequence) or
            isinstance(value, range) or
            hasattr(value, '__array__')
        )
        return ret

    @staticmethod
    def _sanitize_coords(coords: Optional[Union[Sequence, np.ndarray]]) -> np.ndarray:
        """Sanitize the **coords** arguments in :meth:`_MultiMolecule.__new__`."""
        if not _MultiMolecule._is_array_like(coords):
            raise TypeError(_type_error.format('coords', coords.__class__.__name__))
        ret = np.asarray(coords)

        if not ret.ndim == 3 or ret.shape[2] != 3:
            shape = '*'.join('{:d}'.format(i) for i in ret.shape)
            print(_shape_warning.format('coords', shape))

        i = get_nested_element(ret)
        if not isinstance(i, (float, np.float)):
            print(_dtype_warning.format('ret', i.__class__.__name__))

        return ret

    @staticmethod
    def _sanitize_bonds(bonds: Optional[Union[Sequence, np.ndarray]]) -> np.ndarray:
        """Sanitize the **bonds** arguments in :meth:`_MultiMolecule.__new__`."""
        if bonds is None:
            return np.empty((0, 3), dtype=int)
        elif not isinstance(bonds, abc.Collection):
            raise TypeError(_type_error.format('bonds', bonds.__class__.__name__))

        ret = np.asarray(bonds, dtype=int)
        if not ret.ndim == 2:
            print(_shape_warning.format('bonds', ret.ndim))
        return ret

    @staticmethod
    def _sanitize_atoms(atoms: Optional[Dict[str, List[int]]]) -> Dict[str, List[int]]:
        """Sanitize the **atoms** arguments in :meth:`_MultiMolecule.__new__`."""
        type_error = "The 'atoms' argument expects a 'dict' object. A '{}' object was supplied"

        if atoms is None:
            return {}
        elif not isinstance(atoms, dict):
            raise TypeError(type_error.format('atoms', atoms.__class__.__name__))
        return atoms

    @staticmethod
    def _sanitize_properties(properties: Optional[dict]) -> Settings:
        """Sanitize the **properties** arguments in :meth:`_MultiMolecule.__new__`."""
        type_error = "The 'properties' argument expects a 'dict' object. A '{}' object was supplied"

        if properties is None:
            return Settings()
        elif not isinstance(properties, dict):
            raise TypeError(type_error.format('properties', properties.__class__.__name__))
        return Settings(properties)

    """##############################  plams-based properties  ############################### """

    @property
    def atom12(self) -> _MultiMolecule:
        """Get or set the indices of the atoms for all bonds in
        :attr:`.MultiMolecule.bonds` as 2D array."""
        return self.bonds[:, 0:2]

    @atom12.setter
    def atom12(self, value: np.ndarray) -> None:
        self.bonds[:, 0:2] = value

    @property
    def atom1(self) -> _MultiMolecule:
        """Get or set the indices of the first atoms in all bonds of
        :attr:`.MultiMolecule.bonds` as 1D array."""
        return self.bonds[:, 0]

    @atom1.setter
    def atom1(self, value: np.ndarray) -> None:
        self.bonds[:, 0] = value

    @property
    def atom2(self) -> np.ndarray:
        """Get or set the indices of the second atoms in all bonds of
        :attr:`.MultiMolecule.bonds` as 1D array."""
        return self.bonds[:, 1]

    @atom2.setter
    def atom2(self, value: np.ndarray) -> None:
        self.bonds[:, 1] = value

    @property
    def order(self) -> np.ndarray:
        """Get or set the bond orders for all bonds in :attr:`.MultiMolecule.bonds` as 1D array."""
        return self.bonds[:, 2] / 10.0

    @order.setter
    def order(self, value: np.ndarray) -> None:
        self.bonds[:, 2] = value * 10

    @property
    def x(self) -> _MultiMolecule:
        """Get or set the x coordinates for all atoms in instance as 2D array."""
        return self[:, :, 0]

    @x.setter
    def x(self, value: np.ndarray) -> None:
        self[:, :, 0] = value

    @property
    def y(self) -> _MultiMolecule:
        """Get or set the y coordinates for all atoms in this instance as 2D array."""
        return self[:, :, 1]

    @y.setter
    def y(self, value: _MultiMolecule) -> None:
        self[:, :, 1] = value

    @property
    def z(self) -> _MultiMolecule:
        """Get or set the z coordinates for all atoms in this instance as 2D array."""
        return self[:, :, 2]

    @z.setter
    def z(self, value: np.ndarray) -> None:
        self[:, :, 2] = value

    @property
    def symbol(self) -> np.ndarray:
        """Get the atomic symbols of all atoms in :attr:`.MultiMolecule.atoms` as 1D array."""
        return self._get_atomic_property('symbol')

    @property
    def atnum(self) -> np.ndarray:
        """Get the atomic numbers of all atoms in :attr:`.MultiMolecule.atoms` as 1D array."""
        return self._get_atomic_property('atnum')

    @property
    def mass(self) -> np.ndarray:
        """Get the atomic masses of all atoms in :attr:`.MultiMolecule.atoms` as 1D array."""
        return self._get_atomic_property('mass')

    @property
    def radius(self) -> np.ndarray:
        """Get the atomic radii of all atoms in :attr:`.MultiMolecule.atoms` as 1d array."""
        return self._get_atomic_property('radius')

    @property
    def connectors(self) -> np.ndarray:
        """Get the atomic connectors of all atoms in :attr:`.MultiMolecule.atoms` as 1D array."""
        return self._get_atomic_property('connectors')

    def _get_atomic_property(self, prop: str = 'symbol') -> np.ndarray:
        """Create a flattened array with atomic properties.

        Take **self.atoms** and return an (concatenated) array of a specific property associated
        with an atom type. Values are sorted by their indices.

        Parameters
        ----------
        prop : str
            The name of the to be returned property.
            Accepted values: ``"symbol"``, ``"atnum"``, ``"mass"``, ``"radius"``
            or ``"connectors"``.
            See the |PeriodicTable|_ class of PLAMS for more details.

        Returns
        -------
        :math:`n` |np.array|_ [|np.float64|_, |str|_ or |np.int64|_]:
            A 1D array with the user-specified properties of :math:`n` atoms.

        """
        # Create a concatenated lists of the keys and values in **self.atoms**
        prop_list: list = []
        for at, i in self.atoms.items():
            try:
                at_prop = _prop_dict[prop](at)
            except PTError:  # A custom atom is encountered
                at_prop = _none_dict[prop]
                err = "KeyWarning: No {} available for {}, defaulting to '{}'"
                print(err.format(prop, at, str(at_prop)))
            prop_list += [at_prop] * len(i)

        # Sort and return
        idx_gen = itertools.chain.from_iterable(self.atoms.values())
        return np.array([prop for _, prop in sorted(zip(idx_gen, prop_list))])

    """##################################  Magic methods  #################################### """

    def copy(self, order: str = 'C', deep: bool = True) -> _MultiMolecule:
        """Create a copy of this instance.

        .. _np.ndarray.copy: https://docs.scipy.org/doc/numpy/reference/generated/numpy.ndarray.copy.html  # noqa

        Parameters
        ----------
        order : str
            Controls the memory layout of the copy.
            See np.ndarray.copy_ for details.

        copy_attr : bool
            Whether or not the attributes of this instance should be returned as copies or views.

        Returns
        -------
        |FOX.MultiMolecule|_:
            A copy of this instance.

        """
        ret = super().copy(order)
        if not deep:
            return ret

        # Copy attributes
        copy_func = pycopy.deepcopy if deep else pycopy.copy
        for key, value in vars(self).items():
            try:
                setattr(ret, key, value.copy())
            except AttributeError:
                setattr(ret, key, copy_func(value))
        return ret

    def __copy__(self) -> _MultiMolecule:
        """Create copy of this instance."""
        return self.copy(order='K', deep=False)

    def __deepcopy__(self, memo: None) -> _MultiMolecule:
        """Create a deep copy of this instance."""
        return self.copy(order='K', deep=True)

    def __str__(self) -> str:
        """Return a human-readable string constructed from this instance."""
        def _str(k: str, v: Any) -> str:
            key = str(k)
            str_list = self._ndrepr.repr(v).split('\n')
            joiner = '\n' + (3 + len(key)) * ' '
            return f'{k} = ' + joiner.join(i for i in str_list)

        ret = f'{self._ndrepr.repr(self)},\n\n'
        ret += ',\n\n'.join(_str(k, v) for k, v in vars(self).items() if k[0] != '_')
        ret_indent = textwrap.indent(ret, '    ')
        return f'{self.__class__.__name__}(\n{ret_indent}\n)'

    def __repr__(self) -> str:
        """Return the canonical string representation of this instance."""
        return f'{self.__class__.__name__}(..., shape={self.shape}, dtype={repr(self.dtype.name)})'
