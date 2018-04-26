# -*- coding: utf-8 -*-
"""
Created on Fri Apr  6 15:42:22 2018

@author: mpinkert
"""


import mp_img_manip.bulk_img_processing as blk
import pandas as pd
import numpy as np
from pathlib import Path


def parse_index(roi_str):
    
    sample, modality, thresholds, roi = blk.file_name_parts(roi_str)
    return sample, modality, thresholds, roi


def bulk_parse_index(roi_list):
    indices_list = blk.file_name_parts_list(roi_list)
    parsed_indices = np.array(indices_list)
    return parsed_indices


def clean_indices(parsed_indices):
    
    pre_variable_sort_index = ['Sample', 'Modality', 'Thresholds', 'ROI']
    transposed_indices = np.transpose(parsed_indices)
    mid_clean_index = pd.MultiIndex.from_arrays(transposed_indices,
                                          names = pre_variable_sort_index)
    
    return mid_clean_index


def clean_single_dataframe(dirty_frame):
    """Takes a raw cytospectre dataframe and resorts it for easy analysis"""
    
    new_label_dict = {'Mean orientation' : 'Orientation', 
                       'Circ. variance' : 'Alignment'}
    relabeled_frame = dirty_frame.rename(columns = new_label_dict)
    cutdown_frame = relabeled_frame[['Orientation', 'Alignment']]
        
    parsed_indices = bulk_parse_index(list(cutdown_frame.index))  
    clean_index = clean_indices(parsed_indices)  
    clean_frame_stacked = cutdown_frame.set_index(clean_index)
    
    clean_frame = clean_frame_stacked.unstack(1)
    
    return clean_frame


def clean_multiple_dataframes(analysis_list, output_dir, output_suffix):
    
    dirty_index = 'Image'
    relevant_cols = ['Mean orientation', 'Circ. variance']
    dirty_dataframes = blk.dataframe_generator_excel(analysis_list, 
                                                     dirty_index,
                                                     relevant_cols)


    for dirty_frame in dirty_dataframes:
        clean_dataframe = clean_single_dataframe(dirty_frame)
        output_path = Path(output_dir, clean_dataframe.name, 
                           '-', output_suffix)
        
        clean_dataframe.to_csv(output_path)
    
