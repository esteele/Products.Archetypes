# -*- coding: UTF-8 -*-
################################################################################
#
# Copyright (c) 2002-2005, Benjamin Saller <bcsaller@ideasuite.com>, and
#                              the respective authors. All rights reserved.
# For a list of Archetypes contributors see docs/CREDITS.txt.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# * Redistributions of source code must retain the above copyright notice, this
#   list of conditions and the following disclaimer.
# * Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
# * Neither the name of the author nor the names of its contributors may be used
#   to endorse or promote products derived from this software without specific
#   prior written permission.
#
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
################################################################################

from Acquisition import aq_base
from AccessControl import ClassSecurityInfo

from Products.Archetypes.interfaces.storage import IStorage
from Products.Archetypes.interfaces.layer import ILayer
from Products.Archetypes.debug import log
from Products.Archetypes.Storage import Storage
from Products.Archetypes.Storage import StorageLayer
from Products.Archetypes.Storage import _marker
from Products.Archetypes.annotations import AT_ANN_STORAGE
from Products.Archetypes.annotations import AT_MD_STORAGE
from Products.Archetypes.annotations import getAnnotation
from Products.Archetypes.Registry import setSecurity
from Products.Archetypes.Registry import registerStorage

class BaseAnnotationStorage(Storage):
    """Stores data using annotations on the instance
    """

    __implements__ = IStorage

    security = ClassSecurityInfo()

    _key = None
    
    def __init__(self, migrate=False):
        self._migrate = migrate
        
    def _migration(self, name, instance, **kwargs):
        """Migrates data from the original storage
        """
        raise NotImplementedError

    security.declarePrivate('get')
    def get(self, name, instance, **kwargs):
        ann = getAnnotation(instance)
        value = ann.getSubkey(self._key, subkey=name, default=_marker)
        if value is _marker:
            if self._migrate:
                value = self._migration(name, instance, **kwargs)
            else:
                raise AttributeError(name)
        return value

    security.declarePrivate('set')
    def set(self, name, instance, value, **kwargs):
        # Remove acquisition wrappers
        value = aq_base(value)
        ann = getAnnotation(instance)
        ann.setSubkey(self._key, value, subkey=name)

    security.declarePrivate('unset')
    def unset(self, name, instance, **kwargs):
        ann = getAnnotation(instance)
        try:
            ann.delSubkey(self._key, subkey=name)
        except KeyError:
            pass

setSecurity(BaseAnnotationStorage)

class AnnotationStorage(BaseAnnotationStorage):
    """Stores values as ATAnnotations on the object
    """

    _key = AT_ANN_STORAGE

    security = ClassSecurityInfo()
    
    def _migration(self, name, instance, **kwargs):
        """Migrates data from the original storage
        """
        value = getattr(aq_base(instance), name, _marker)
        if value is _marker:
                raise AttributeError(name)
        self.set(name, instance, value, **kwargs)
        delattr(instance, name)
        return value

registerStorage(AnnotationStorage)

class MetadataAnnotationStorage(BaseAnnotationStorage, StorageLayer):
    """Stores metadata as ATAnnotations on the object
    """

    _key = AT_MD_STORAGE

    security = ClassSecurityInfo()

    __implements__ = (IStorage, ILayer,)
    
    def _migration(self, name, instance, **kwargs):
        """Migrates data from the original storage
        """
        try:
            md = aq_base(instance)._md
            value = md[name]
        except KeyError, msg:
            # We are acting like an attribute, so
            # raise AttributeError instead of KeyError
            raise AttributeError(name, msg)
        self.set(name, instance, value, **kwargs)
        del md[name]
        return value

    security.declarePrivate('initializeInstance')
    def initializeInstance(self, instance, item=None, container=None):
        # annotations are initialized on first access
        pass

    security.declarePrivate('initializeField')
    def initializeField(self, instance, field):
        # Check for already existing field to avoid  the reinitialization
        # (which means overwriting) of an already existing field after a
        # copy or rename operation
        ann = getAnnotation(instance)
        if not ann.hasSubkey(self._key, subkey=field.getName()):
            self.set(field.getName(), instance, field.getDefault(instance))

    security.declarePrivate('cleanupField')
    def cleanupField(self, instance, field, **kwargs):
        # Don't clean up the field self to avoid problems with copy/rename. The
        # python garbarage system will clean up if needed.
        pass

    security.declarePrivate('cleanupInstance')
    def cleanupInstance(self, instance, item=None, container=None):
        # Don't clean up the instance self to avoid problems with copy/rename. The
        # python garbarage system will clean up if needed.
        pass

registerStorage(MetadataAnnotationStorage)
