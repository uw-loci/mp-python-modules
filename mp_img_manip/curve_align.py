# -*- coding: utf-8 -*-
"""
Created on Wed Jun  6 10:19:59 2018

@author: mpinkert
"""

import mp_img_manip.bulk_img_processing as blk
import mp_img_manip.tiling as til
import mp_img_manip.utility_functions as util

import SimpleITK as sitk
import os
import numpy as np
import pandas as pd
import scipy.io as sio
from pathlib import Path
import datetime
import tarfile
import csv


def create_rois_from_tile(tile, roi_size):

    date = str(datetime.date.today())
    t = datetime.datetime.now()
    time = str(t.hour) + ':' + str(t.minute) + ':' + str(t.second)
    roi_shape = 1

    tile_dim = np.shape(tile)

    num_rois, roi_offset = til.calculate_number_of_tiles(tile_dim, roi_size, roi_size)

    separate_rois = {}

    for start, end, roi_number in til.generate_tile_start_end_index(num_rois, roi_size,
                                                                    roi_offset):

        start = start + 1
        end = end + 1

        roi_def = [start[0], start[1], roi_size[0], roi_size[1]]
        enclosing_rect = [start[0], start[1], end[0], end[1]]
        ym = start[1] + roi_size[1]/2
        xm = start[0] + roi_size[0]/2
        boundary = np.array((1,), dtype=np.object)
        boundary_object = np.array([
                    [start[0], start[1]],
                    [start[0], end[1]],
                    [end[0], end[1]],
                    [end[0], start[1]],
                    [start[0], start[1]]])
        boundary[0] = boundary_object
    
        roi = {
            'date': date,
            'time': time,
            'shape': roi_shape,
            'roi': roi_def,
            'enclosing_rect': enclosing_rect,
            'ym': ym,
            'xm': xm,
            'boundary': boundary
        }

        roi_name = 'ROI' + str(roi_number[0]) + 'x' + str(roi_number[1]) + 'y'

        separate_rois[roi_name] = roi

    return separate_rois


def save_rois(image_path, output_dir, output_suffix, tile_number, separate_rois):

    roi_suffix = output_suffix + '_' + str(tile_number[0]) + 'x-' + str(tile_number[1]) + 'y' \
                  + '_ROIs'

    roi_dir = Path(output_dir, 'ROI_management')
    os.makedirs(roi_dir, exist_ok=True)

    rois_path = blk.create_new_image_path(image_path, roi_dir, roi_suffix, extension='.mat')

    sio.savemat(str(rois_path), separate_rois)

    return


def process_image_to_rois(image_path, output_dir, output_suffix='Tile',
                          tile_size=np.array([512, 512]), tile_separation=np.array([512, 512]),
                          roi_size=np.array([64, 64]),
                          intensity_threshold=1, number_threshold=10,
                          skip_existing_images=True):

    image = sitk.ReadImage(str(image_path))
    image_array = sitk.GetArrayFromImage(image)
    max_value = np.max(image_array)

    for tile, tile_number in til.generate_tile(image_array, tile_size, tile_separation=tile_separation):

        if til.tile_passes_threshold(tile, intensity_threshold, number_threshold, max_value):

            separate_rois = {'separate_rois': create_rois_from_tile(tile, roi_size)}
            save_rois(image_path, output_dir, output_suffix,
                      tile_number, separate_rois)
            til.write_tile(tile, image_path, output_dir, output_suffix,
                           tile_number[0], tile_number[1],
                           skip_existing_images=skip_existing_images)


def construct_job_file(tile_list, job_path):
    with tarfile.open(job_path, 'w') as tar:
        roi_dir = tarfile.TarInfo('ROI_management')
        roi_dir.type = tarfile.DIRTYPE
        roi_dir.mode = 0o777

        for tile in tile_list:
            tar.add(tile, arcname=tile.name, recursive=False)
            roi_path = Path(tile.parent, 'ROI_management', tile.stem + '_ROIs.mat')
            tar_roi_name = Path('ROI_management', roi_path.name)
            tar.add(roi_path, arcname=tar_roi_name, recursive=False)


def process_folder_to_jobs(image_path, tile_dir, output_dir, output_suffix,
                           batch_size,
                           skip_existing_images=True):

    tile_list = util.list_filetype_in_dir(tile_dir, '.tif')
    lists_of_job_items = util.split_list_into_sublists(tile_list, batch_size)
    list_suffix = output_suffix + '_JobList'

    job_list_path = blk.create_new_image_path(image_path, output_dir, list_suffix, extension='.csv')
    job_number = 1

    os.makedirs(output_dir, exist_ok=True)
    job_list = open(job_list_path, 'w')

    for tile_list in lists_of_job_items:
        job_suffix = output_suffix + '_Job-' + str(job_number)
        job_path = blk.create_new_image_path(image_path, output_dir, job_suffix, extension='.tar')
        job_number += 1

        if job_path.exists() and skip_existing_images:
            continue

        construct_job_file(tile_list, job_path)
        job_list.write(job_path.name + '\n')


def create_batches_for_chtc(input_dir, output_dir, output_suffix,
                            tile_size=np.array([512, 512]), tile_separation=np.array([512, 512]),
                            roi_size=np.array([64, 64]),
                            intensity_threshold=1,
                            number_threshold=10,
                            batch_size=10,
                            skip_existing_images=True):

    image_path_list = util.list_filetype_in_subdirs(input_dir, '.tif')

    # want to split on sample name...

    for path in image_path_list:
        print('Tiling {0} for CHTC and Cytospectre analysis'.format(path.name))
        tile_dir = Path(output_dir, blk.get_core_file_name(path))
        os.makedirs(tile_dir, exist_ok=True)

        process_image_to_rois(path, tile_dir, output_suffix=output_suffix,
                              tile_size=tile_size, tile_separation=tile_separation,
                              roi_size=roi_size,
                              intensity_threshold=intensity_threshold, number_threshold=number_threshold,
                              skip_existing_images=skip_existing_images)

        batch_dir = Path(tile_dir, 'Batches')

        process_folder_to_jobs(path, tile_dir, batch_dir, output_suffix,
                               batch_size,
                               skip_existing_images)

    return


def read_stats_file(stats_file):

    dirty_df = pd.read_csv(stats_file, delimiter='\t', header=None)
    orientation = dirty_df[1].loc[0]
    alignment = dirty_df[1].loc[4]

    return orientation, alignment


def scrape_results(images_dir, output_dir, output_suffix):

    tile_dir = Path(images_dir, 'CA_Out')
    roi_dir = Path(images_dir, 'CA_ROI\Batch\ROI_post_analysis')

    tile_files = util.list_filetype_in_dir(tile_dir, 'stats.csv')
    roi_files = util.list_filetype_in_dir(roi_dir, 'stats.csv')

    csv_path = Path(output_dir, 'Curve_Align_results' + output_suffix + '.csv')

    with open(csv_path, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Sample', 'Modality', 'Tile', 'ROI', 'Orientation', 'Alignment'])

        for tile_path in tile_files:
            sample, modality, tile = blk.file_name_parts(tile_path)[:3]
            roi = 'Full-tile'
            orientation, alignment = read_stats_file(tile_path)
            writer.writerow([sample, modality, tile, roi, orientation, alignment])

        for roi_path in roi_files:
            sample, modality, tile, roi = blk.file_name_parts(roi_path)[:4]
            orientation, alignment = read_stats_file(roi_path)
            writer.writerow([sample, modality, tile, roi, orientation, alignment])


def load_dataframe(csv_path):
    raw_df = pd.read_csv(csv_path)

    clean_df = pd.pivot_table(raw_df, index=['Sample', 'Tile', 'ROI'],
                              values=['Alignment', 'Orientation'],
                              columns='Modality')

    return clean_df