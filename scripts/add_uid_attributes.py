#!/usr/bin/env python
###
# Copyright 2015-2024, Institute for Systems Biology
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
###

"""
Script to add PatientID, StudyInstanceUID, and SeriesInstanceUID as filterable
Attributes in the database. These attributes are set with default_ui_display=False
so they can be used for URL filtering without cluttering the UI filter panels.

Usage:
    python scripts/add_uid_attributes.py [--dry-run]
"""

from __future__ import print_function
import os
import sys
import logging
from argparse import ArgumentParser

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "idc.settings")

import django
django.setup()

from django.core.exceptions import ObjectDoesNotExist
from idc_collections.models import Attribute, DataSource, DataSetType, Attribute_Set_Type

logger = logging.getLogger(__name__)

# UID attributes to add - these are high-cardinality fields that should be
# available for URL filtering but not shown in the UI filter panels
UID_ATTRIBUTES = [
    {
        'name': 'PatientID',
        'display_name': 'Patient ID',
        'data_type': 'S',  # String type
        'default_ui_display': False,  # Don't show in UI filter panels
        'is_cross_collex': True,
    },
    {
        'name': 'StudyInstanceUID',
        'display_name': 'Study Instance UID',
        'data_type': 'S',
        'default_ui_display': False,
        'is_cross_collex': True,
    },
    {
        'name': 'SeriesInstanceUID',
        'display_name': 'Series Instance UID',
        'data_type': 'S',
        'default_ui_display': False,
        'is_cross_collex': True,
    },
]


def add_uid_attributes(dry_run=False):
    """Add UID attributes to the database."""

    # Get the dicom data sources to associate with these attributes
    dicom_sources = DataSource.objects.filter(name__icontains='dicom')

    if not dicom_sources.exists():
        print("Warning: No DICOM data sources found. Attributes will be created without data source associations.")
        print("Available data sources:")
        for ds in DataSource.objects.all():
            print(f"  - {ds.name}")

    for attr_def in UID_ATTRIBUTES:
        try:
            # Check if attribute already exists
            existing = Attribute.objects.filter(name=attr_def['name']).first()

            if existing:
                print(f"Attribute '{attr_def['name']}' already exists (id={existing.id}, default_ui_display={existing.default_ui_display})")

                # Update default_ui_display if needed
                if existing.default_ui_display != attr_def['default_ui_display']:
                    if dry_run:
                        print(f"  [DRY RUN] Would update default_ui_display to {attr_def['default_ui_display']}")
                    else:
                        existing.default_ui_display = attr_def['default_ui_display']
                        existing.save()
                        print(f"  Updated default_ui_display to {attr_def['default_ui_display']}")
            else:
                if dry_run:
                    print(f"[DRY RUN] Would create attribute '{attr_def['name']}':")
                    print(f"  display_name: {attr_def['display_name']}")
                    print(f"  data_type: {attr_def['data_type']}")
                    print(f"  default_ui_display: {attr_def['default_ui_display']}")
                    print(f"  is_cross_collex: {attr_def['is_cross_collex']}")
                else:
                    obj = Attribute.objects.create(
                        name=attr_def['name'],
                        display_name=attr_def['display_name'],
                        data_type=attr_def['data_type'],
                        default_ui_display=attr_def['default_ui_display'],
                        is_cross_collex=attr_def['is_cross_collex'],
                    )
                    print(f"Created attribute '{attr_def['name']}' (id={obj.id})")

                    # Associate with DICOM data sources
                    for ds in dicom_sources:
                        obj.data_sources.add(ds)
                        print(f"  Added to data source: {ds.name}")

                    # Associate with IMAGE_DATA dataset type if it exists
                    try:
                        image_data_type = DataSetType.objects.get(data_type=DataSetType.IMAGE_DATA)
                        Attribute_Set_Type.objects.update_or_create(
                            datasettype=image_data_type,
                            attribute=obj,
                            defaults={'child_record_search': 'StudyInstanceUID'}
                        )
                        print(f"  Associated with dataset type: {image_data_type.name}")
                    except ObjectDoesNotExist:
                        print("  Warning: IMAGE_DATA dataset type not found")
                    except Exception as e:
                        print(f"  Warning: Could not associate with dataset type: {e}")

        except Exception as e:
            print(f"Error processing attribute '{attr_def['name']}': {e}")
            logger.exception(e)

    print("\nDone!")
    if dry_run:
        print("This was a dry run. No changes were made to the database.")


def main():
    parser = ArgumentParser(description='Add UID attributes for URL filtering')
    parser.add_argument('--dry-run', action='store_true',
                        help='Show what would be done without making changes')
    args = parser.parse_args()

    add_uid_attributes(dry_run=args.dry_run)


if __name__ == '__main__':
    main()
