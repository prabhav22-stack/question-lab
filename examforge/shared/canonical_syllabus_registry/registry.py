r"""
ExamForge - Global Canonical Syllabus Registry API
Author: ExamForge Core Team

Single Source of Truth for all Course, Block, Unit, Topic and Subtopic metadata.
Provides strictly read-only access and fails loudly on unknown or ambiguous unit lookups.
"""

import os
import re
import json
import pandas as pd
from typing import Dict, List, Optional, Any, Union

REGISTRY_DIR = os.path.dirname(os.path.abspath(__file__))

class SyllabusRegistryError(Exception):
    """Base exception for all registry lookup and validation errors."""
    pass

class UnitNotFoundError(SyllabusRegistryError):
    """Raised when an invalid course or unit is requested."""
    pass

class CanonicalSyllabusRegistry:
    _instance = None

    def __new__(cls, registry_dir: str = None):
        if cls._instance is None:
            cls._instance = super(CanonicalSyllabusRegistry, cls).__new__(cls)
            cls._instance._init_registry(registry_dir or REGISTRY_DIR)
        return cls._instance

    def _init_registry(self, registry_dir: str):
        self.registry_dir = registry_dir
        
        # Load courses
        course_p = os.path.join(registry_dir, 'course_registry.csv')
        if not os.path.exists(course_p):
            raise SyllabusRegistryError(f"Registry course file not found at: {course_p}")
        self.df_courses = pd.read_csv(course_p)
        self.courses_by_code = {r['course_code']: r.to_dict() for _, r in self.df_courses.iterrows()}

        # Load blocks
        block_p = os.path.join(registry_dir, 'block_registry.csv')
        self.df_blocks = pd.read_csv(block_p)

        # Load units
        unit_p = os.path.join(registry_dir, 'unit_registry.csv')
        self.df_units = pd.read_csv(unit_p)
        
        # Index units by canonical_id and (course, unit_number)
        self.units_by_id = {}
        self.units_by_course_num = {}
        for _, r in self.df_units.iterrows():
            d = r.to_dict()
            cid = str(d['canonical_unit_id']).strip()
            self.units_by_id[cid] = d
            
            c_code = str(d['course_code']).strip().upper()
            u_num = int(d['unit_number'])
            self.units_by_course_num[(c_code, u_num)] = d

        # Load topics
        topic_p = os.path.join(registry_dir, 'topic_registry.csv')
        self.df_topics = pd.read_csv(topic_p)
        self.topics_by_unit = {}
        for _, r in self.df_topics.iterrows():
            uid = r['canonical_unit_id']
            if uid not in self.topics_by_unit:
                self.topics_by_unit[uid] = []
            self.topics_by_unit[uid].append(r.to_dict())

        # Load subtopics
        subtopic_p = os.path.join(registry_dir, 'subtopic_registry.csv')
        self.df_subtopics = pd.read_csv(subtopic_p)
        self.subtopics_by_unit = {}
        for _, r in self.df_subtopics.iterrows():
            uid = r['canonical_unit_id']
            if uid not in self.subtopics_by_unit:
                self.subtopics_by_unit[uid] = []
            self.subtopics_by_unit[uid].append(r.to_dict())

        # Load known aliases
        alias_p = os.path.join(registry_dir, 'known_aliases.csv')
        self.df_aliases = pd.read_csv(alias_p) if os.path.exists(alias_p) else pd.DataFrame()

        # Load sources
        source_p = os.path.join(registry_dir, 'syllabus_sources.csv')
        self.df_sources = pd.read_csv(source_p) if os.path.exists(source_p) else pd.DataFrame()

    def normalize_course_code(self, course_code: str) -> str:
        c = course_code.strip().upper()
        if re.match(r'^MPA\d{3}$', c):
            c = f"{c[:3]}-{c[3:]}"
        return c

    def get_course(self, course_code: str) -> Dict[str, Any]:
        c = self.normalize_course_code(course_code)
        if c not in self.courses_by_code:
            raise UnitNotFoundError(f"Course code '{course_code}' not found in canonical course registry.")
        return self.courses_by_code[c]

    def get_unit(self, course_code: str, unit_number: int) -> Dict[str, Any]:
        c = self.normalize_course_code(course_code)
        key = (c, int(unit_number))
        if key not in self.units_by_course_num:
            raise UnitNotFoundError(
                f"Unit {unit_number} not found for course '{course_code}'. "
                f"Valid units for {c} are 1 to {self.get_course(c)['total_units']}."
            )
        return self.units_by_course_num[key]

    def get_unit_by_id(self, canonical_unit_id: str) -> Dict[str, Any]:
        cid = canonical_unit_id.strip()
        if cid not in self.units_by_id:
            raise UnitNotFoundError(f"Canonical Unit ID '{canonical_unit_id}' not found in registry.")
        return self.units_by_id[cid]

    def get_units_by_course(self, course_code: str) -> List[Dict[str, Any]]:
        c = self.normalize_course_code(course_code)
        sub = self.df_units[self.df_units['course_code'] == c]
        if sub.empty:
            raise UnitNotFoundError(f"No units registered for course '{course_code}'.")
        return [r.to_dict() for _, r in sub.sort_values('unit_number').iterrows()]

    def get_units_by_block(self, course_code: str, block_number: int) -> List[Dict[str, Any]]:
        c = self.normalize_course_code(course_code)
        sub = self.df_units[(self.df_units['course_code'] == c) & (self.df_units['block_number'] == int(block_number))]
        if sub.empty:
            raise UnitNotFoundError(f"No units found for course '{course_code}', Block {block_number}.")
        return [r.to_dict() for _, r in sub.sort_values('unit_number').iterrows()]

    def get_topics(self, canonical_unit_id: str) -> List[Dict[str, Any]]:
        cid = canonical_unit_id.strip()
        return self.topics_by_unit.get(cid, [])

    def get_subtopics(self, canonical_unit_id: str) -> List[Dict[str, Any]]:
        cid = canonical_unit_id.strip()
        return self.subtopics_by_unit.get(cid, [])

    def validate_question_mapping(self, question_record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validates that a question record references a real, canonical unit.
        Fails loudly if course or unit is unknown. Never falls back to Unit 1 silently.
        """
        course = question_record.get('course_code') or question_record.get('course')
        unit = question_record.get('unit_number') or question_record.get('unit') or question_record.get('unit_id')
        
        if not course or unit is None:
            raise SyllabusRegistryError(f"Question record missing required 'course' or 'unit' fields: {question_record}")
            
        try:
            canon_unit = self.get_unit(str(course), int(unit))
            return {
                'is_valid': True,
                'canonical_unit_id': canon_unit['canonical_unit_id'],
                'official_unit_title': canon_unit['official_unit_title'],
                'block_number': canon_unit['block_number'],
                'nominal_section': canon_unit['nominal_section']
            }
        except UnitNotFoundError as e:
            raise SyllabusRegistryError(f"Invalid question mapping in record {question_record}: {e}")

# Global singleton accessors
_global_registry = None

def get_registry() -> CanonicalSyllabusRegistry:
    global _global_registry
    if _global_registry is None:
        _global_registry = CanonicalSyllabusRegistry()
    return _global_registry

def get_course(course_code: str) -> Dict[str, Any]:
    return get_registry().get_course(course_code)

def get_unit(course_code: str, unit_number: int) -> Dict[str, Any]:
    return get_registry().get_unit(course_code, unit_number)

def get_unit_by_id(canonical_unit_id: str) -> Dict[str, Any]:
    return get_registry().get_unit_by_id(canonical_unit_id)

def get_units_by_course(course_code: str) -> List[Dict[str, Any]]:
    return get_registry().get_units_by_course(course_code)

def get_units_by_block(course_code: str, block_number: int) -> List[Dict[str, Any]]:
    return get_registry().get_units_by_block(course_code, block_number)

def get_topics(canonical_unit_id: str) -> List[Dict[str, Any]]:
    return get_registry().get_topics(canonical_unit_id)

def get_subtopics(canonical_unit_id: str) -> List[Dict[str, Any]]:
    return get_registry().get_subtopics(canonical_unit_id)

def validate_question_mapping(question_record: Dict[str, Any]) -> Dict[str, Any]:
    return get_registry().validate_question_mapping(question_record)
