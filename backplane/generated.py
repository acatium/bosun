# Generated from model/bosun.yaml by gen-pydantic. Do not edit; regenerate with: model/.venv/bin/gen-pydantic model/bosun.yaml
from __future__ import annotations

import re
import sys
from datetime import (
    date,
    datetime,
    time
)
from decimal import Decimal
from enum import Enum
from typing import (
    Any,
    ClassVar,
    Literal,
    Optional,
    Union
)

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    RootModel,
    SerializationInfo,
    SerializerFunctionWrapHandler,
    field_validator,
    model_serializer
)


metamodel_version = "1.12.0"
version = "None"


class ConfiguredBaseModel(BaseModel):
    model_config = ConfigDict(
        serialize_by_alias = True,
        validate_by_name = True,
        validate_assignment = True,
        validate_default = True,
        extra = "forbid",
        arbitrary_types_allowed = True,
        use_enum_values = True,
        strict = False,
    )





class LinkMLMeta(RootModel):
    root: dict[str, Any] = {}
    model_config = ConfigDict(frozen=True)

    def __getattr__(self, key:str):
        return getattr(self.root, key)

    def __getitem__(self, key:str):
        return self.root[key]

    def __setitem__(self, key:str, value):
        self.root[key] = value

    def __contains__(self, key:str) -> bool:
        return key in self.root


linkml_meta = LinkMLMeta({'default_prefix': 'bosun',
     'default_range': 'string',
     'description': 'The primitives that people, agents and systems reason about: '
                    'domains, roles, business terms, stores and entitlement rules '
                    'over tags. Holds only what changes slowly. Deal room '
                    'instances, membership and documents belong to Microsoft 365, '
                    'not to this model.',
     'id': 'https://example.org/bosun',
     'imports': ['linkml:types'],
     'license': 'MIT',
     'name': 'bosun',
     'prefixes': {'bosun': {'prefix_prefix': 'bosun',
                            'prefix_reference': 'https://example.org/bosun/'},
                  'linkml': {'prefix_prefix': 'linkml',
                             'prefix_reference': 'https://w3id.org/linkml/'}},
     'source_file': 'model/bosun.yaml',
     'title': 'Bosun governance primitives'} )

class Sensitivity(str, Enum):
    """
    Sensitivity tags; each maps to a Purview sensitivity label.
    """
    Public = "Public"
    """
    May be shared firm-wide.
    """
    Internal = "Internal"
    """
    Internal to the owning domain.
    """
    Confidential = "Confidential"
    """
    Deal team only. Private, no guests.
    """


class StoreKind(str, Enum):
    DealRoom = "DealRoom"
    """
    A Microsoft 365 group with its SharePoint site, created per deal.
    """
    Workspace = "Workspace"
    """
    A Fabric workspace.
    """
    Dataset = "Dataset"
    """
    A lakehouse table within a workspace.
    """


class Effect(str, Enum):
    allow = "allow"
    deny = "deny"


class Action(str, Enum):
    open = "open"
    """
    Create a new instance of a store template.
    """
    add_member = "add_member"
    """
    Add a person to a store instance.
    """
    read = "read"
    """
    Read the store's content.
    """


class MemberKind(str, Enum):
    Member = "Member"
    """
    A person in the firm's directory.
    """
    Guest = "Guest"
    """
    Anyone outside the firm.
    """


class Audience(str, Enum):
    Everyone = "Everyone"
    """
    Everyone in the firm.
    """
    DomainMembers = "DomainMembers"
    """
    People in the store's domain.
    """
    StoreMembers = "StoreMembers"
    """
    People added to the store instance.
    """



class Firm(ConfiguredBaseModel):
    """
    The firm and everything the backplane governs.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://example.org/bosun', 'tree_root': True})

    name: str = Field(default=..., json_schema_extra = { "linkml_meta": {'domain_of': ['Firm', 'Domain', 'Role', 'Term', 'Store', 'DealRoomRequest']} })
    domains: list[Domain] = Field(default=..., json_schema_extra = { "linkml_meta": {'domain_of': ['Firm']} })
    roles: list[Role] = Field(default=..., json_schema_extra = { "linkml_meta": {'domain_of': ['Firm']} })
    terms: Optional[list[Term]] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Firm']} })
    stores: Optional[list[Store]] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Firm']} })
    rules: Optional[list[Rule]] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Firm']} })


class Domain(ConfiguredBaseModel):
    """
    A part of the firm that owns data and decisions. Domains nest one level at most.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://example.org/bosun'})

    id: str = Field(default=..., json_schema_extra = { "linkml_meta": {'domain_of': ['Domain', 'Role', 'Term', 'Store', 'Rule']} })
    name: str = Field(default=..., json_schema_extra = { "linkml_meta": {'domain_of': ['Firm', 'Domain', 'Role', 'Term', 'Store', 'DealRoomRequest']} })
    description: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Domain', 'Rule']} })
    parent: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'domain_of': ['Domain']} })
    owner: str = Field(default=..., description="""The role accountable for this domain.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Domain', 'Term']} })

    @field_validator('id')
    def pattern_id(cls, v):
        pattern=re.compile(r"^[a-z][a-z0-9-]*$")
        if isinstance(v, list):
            for element in v:
                if isinstance(element, str) and not pattern.search(element):
                    err_msg = f"Invalid id format: {element}"
                    raise ValueError(err_msg)
        elif isinstance(v, str) and not pattern.search(v):
            err_msg = f"Invalid id format: {v}"
            raise ValueError(err_msg)
        return v


class Role(ConfiguredBaseModel):
    """
    A kind of person. Membership comes from the directory attribute, never by hand.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://example.org/bosun'})

    id: str = Field(default=..., json_schema_extra = { "linkml_meta": {'domain_of': ['Domain', 'Role', 'Term', 'Store', 'Rule']} })
    name: str = Field(default=..., json_schema_extra = { "linkml_meta": {'domain_of': ['Firm', 'Domain', 'Role', 'Term', 'Store', 'DealRoomRequest']} })
    domain: str = Field(default=..., json_schema_extra = { "linkml_meta": {'domain_of': ['Role', 'Term', 'Store']} })
    department: str = Field(default=..., description="""The Entra department value that places a person in this role's domain.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Role']} })
    job_title: Optional[str] = Field(default=None, description="""The Entra job title that distinguishes this role within its domain.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Role']} })

    @field_validator('id')
    def pattern_id(cls, v):
        pattern=re.compile(r"^[a-z][a-z0-9-]*$")
        if isinstance(v, list):
            for element in v:
                if isinstance(element, str) and not pattern.search(element):
                    err_msg = f"Invalid id format: {element}"
                    raise ValueError(err_msg)
        elif isinstance(v, str) and not pattern.search(v):
            err_msg = f"Invalid id format: {v}"
            raise ValueError(err_msg)
        return v


class Term(ConfiguredBaseModel):
    """
    A closed business term. Each term means one thing and binds to one authoritative calculation.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://example.org/bosun'})

    id: str = Field(default=..., json_schema_extra = { "linkml_meta": {'domain_of': ['Domain', 'Role', 'Term', 'Store', 'Rule']} })
    name: str = Field(default=..., json_schema_extra = { "linkml_meta": {'domain_of': ['Firm', 'Domain', 'Role', 'Term', 'Store', 'DealRoomRequest']} })
    definition: str = Field(default=..., json_schema_extra = { "linkml_meta": {'domain_of': ['Term']} })
    domain: str = Field(default=..., json_schema_extra = { "linkml_meta": {'domain_of': ['Role', 'Term', 'Store']} })
    owner: str = Field(default=..., description="""Who approves changes to this term.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Domain', 'Term']} })
    measure: Optional[str] = Field(default=None, description="""The semantic model measure that is the authoritative calculation.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Term']} })
    source: Optional[str] = Field(default=None, description="""The store whose data the measure is calculated from, if not the default.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Term']} })
    calculation: Optional[str] = Field(default=None, description="""The authoritative calculation in the semantic model's language (DAX). The compiler adds the measure if it is missing.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Term']} })
    format_string: Optional[str] = Field(default=None, description="""How the measure is displayed, e.g. 0.0% or #,0. Defaults to #,0.00.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Term']} })

    @field_validator('id')
    def pattern_id(cls, v):
        pattern=re.compile(r"^[a-z][a-z0-9-]*$")
        if isinstance(v, list):
            for element in v:
                if isinstance(element, str) and not pattern.search(element):
                    err_msg = f"Invalid id format: {element}"
                    raise ValueError(err_msg)
        elif isinstance(v, str) and not pattern.search(v):
            err_msg = f"Invalid id format: {v}"
            raise ValueError(err_msg)
        return v


class Store(ConfiguredBaseModel):
    """
    Somewhere data or documents live. Deal rooms are templates; each instance is created on request.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://example.org/bosun'})

    id: str = Field(default=..., json_schema_extra = { "linkml_meta": {'domain_of': ['Domain', 'Role', 'Term', 'Store', 'Rule']} })
    name: str = Field(default=..., json_schema_extra = { "linkml_meta": {'domain_of': ['Firm', 'Domain', 'Role', 'Term', 'Store', 'DealRoomRequest']} })
    kind: StoreKind = Field(default=..., json_schema_extra = { "linkml_meta": {'domain_of': ['Store']} })
    domain: str = Field(default=..., description="""The domain accountable for this store's content. Access is decided per store by the rules, not by domain or tags.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Role', 'Term', 'Store']} })
    sensitivity: Optional[Sensitivity] = Field(default=None, description="""Fixed sensitivity. Deal rooms leave this empty and ask for it on each request.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Store', 'Rule', 'DealRoomRequest']} })
    within: Optional[str] = Field(default=None, description="""The store that contains this one, e.g. the workspace holding a dataset.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Store']} })
    file: Optional[str] = Field(default=None, description="""Repository path of the data loaded into a dataset.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Store']} })
    table: Optional[str] = Field(default=None, description="""Lakehouse table a dataset loads into.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Store']} })

    @field_validator('id')
    def pattern_id(cls, v):
        pattern=re.compile(r"^[a-z][a-z0-9-]*$")
        if isinstance(v, list):
            for element in v:
                if isinstance(element, str) and not pattern.search(element):
                    err_msg = f"Invalid id format: {element}"
                    raise ValueError(err_msg)
        elif isinstance(v, str) and not pattern.search(v):
            err_msg = f"Invalid id format: {v}"
            raise ValueError(err_msg)
        return v


class Rule(ConfiguredBaseModel):
    """
    An entitlement written over roles, stores and tags. The backplane compiles rules into native grants and checks them at request time.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://example.org/bosun'})

    id: str = Field(default=..., json_schema_extra = { "linkml_meta": {'domain_of': ['Domain', 'Role', 'Term', 'Store', 'Rule']} })
    description: str = Field(default=..., json_schema_extra = { "linkml_meta": {'domain_of': ['Domain', 'Rule']} })
    effect: Effect = Field(default=..., json_schema_extra = { "linkml_meta": {'domain_of': ['Rule']} })
    action: Action = Field(default=..., json_schema_extra = { "linkml_meta": {'domain_of': ['Rule']} })
    role: Optional[str] = Field(default=None, description="""Applies to people in this role. Empty means anyone.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Rule']} })
    store: Optional[str] = Field(default=None, description="""Applies to this store. Empty means any store.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Rule']} })
    sensitivity: Optional[Sensitivity] = Field(default=None, description="""Applies only when the store has this sensitivity.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Store', 'Rule', 'DealRoomRequest']} })
    member_kind: Optional[MemberKind] = Field(default=None, description="""For add_member, the kind of person being added.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Rule']} })
    audience: Optional[Audience] = Field(default=None, description="""For read, who may read.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Rule']} })

    @field_validator('id')
    def pattern_id(cls, v):
        pattern=re.compile(r"^[a-z][a-z0-9-]*$")
        if isinstance(v, list):
            for element in v:
                if isinstance(element, str) and not pattern.search(element):
                    err_msg = f"Invalid id format: {element}"
                    raise ValueError(err_msg)
        elif isinstance(v, str) and not pattern.search(v):
            err_msg = f"Invalid id format: {v}"
            raise ValueError(err_msg)
        return v


class DealRoomRequest(ConfiguredBaseModel):
    """
    What a person must supply to open a deal room. The backplane's create_deal_room tool takes its input schema from this class, so an agent cannot call it without every required field.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://example.org/bosun'})

    name: str = Field(default=..., description="""The deal's code name, e.g. Project Atlas.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Firm', 'Domain', 'Role', 'Term', 'Store', 'DealRoomRequest']} })
    members: list[str] = Field(default=..., description="""Email addresses of the deal team.""", json_schema_extra = { "linkml_meta": {'domain_of': ['DealRoomRequest']} })
    sensitivity: Sensitivity = Field(default=..., description="""How confidential the deal is. Never defaulted.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Store', 'Rule', 'DealRoomRequest']} })
    file_from_inbox: Optional[str] = Field(default=None, description="""Optional text in the subject of the email to file from. The most recent matching email is used, and only its document attachments are filed.""", json_schema_extra = { "linkml_meta": {'domain_of': ['DealRoomRequest']} })


# Model rebuild
# see https://pydantic-docs.helpmanual.io/usage/models/#rebuilding-a-model
Firm.model_rebuild()
Domain.model_rebuild()
Role.model_rebuild()
Term.model_rebuild()
Store.model_rebuild()
Rule.model_rebuild()
DealRoomRequest.model_rebuild()
