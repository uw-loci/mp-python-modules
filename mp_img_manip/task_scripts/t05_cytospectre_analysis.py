# -*- coding: utf-8 -*-
"""
Created on Mon Apr  2 16:03:35 2018

@author: mpinkert
"""

import mp_img_manip.dir_dictionary as dird
import mp_img_manip.bulk_img_processing as blk
import mp_img_manip.utility_functions as util
import pandas as pd
import os


def parse_index(roi_str):
    
    sample, modality, roi = blk.file_name_parts(roi_str)
    return sample, modality, roi


def dataframe_generator(analysis_list):
    

    #read in the dataframes
    for item in analysis_list:
           yield pd.read_excel(item, usecols = relevant_cols, index_col = index)
    
        

def clean_single_dataframe(dirty_frame):
    index = ['Sample', 'ROI', 'Variable']
    column_labels = ['PS', 'SHG', 'MMP']     
    clean_dataframe = pd.DataFrame(columns = column_labels)
    clean_dataframe.set_index(index)
    
    
    
    
    #The current loop is low efficiency, as it is value-wise changes and pandas
    #Copies the whole dataframe every operation
    
    
    for index, row in dirty_frame.iterrows():
        sample, modality, roi = parse_index(index)
        clean_dataframe.loc[(sample, roi,'Orientation'), modality] = row[0]
        clean_dataframe.loc[(sample, roi,'Alignment'), modality] = row[1]
        
    return clean_dataframe

def clean_up_dataframes(analysis_list):
    
    dirty_index = 'Image'
    relevant_cols = ['Image', 'Mean orientation', 'Circ. variance']
    dirty_dataframes = blk.dataframe_generator_excel(analysis_list, 
                                                     dirty_index,
                                                     relevant_cols)

    index = ['Sample', 'ROI', 'Variable']
    column_labels = ['PS', 'SHG', 'MMP']     
    clean_dataframes = pd.DataFrame(columns = column_labels)
    clean_dataframes.set_index(index)

    for dirty_frame in dirty_dataframes:
        dataframe = clean_single_dataframe(dirty_frame)
        clean_dataframes.append(dataframe)   
        
    return clean_dataframes
    


def write_roi_comparison_file(sample_dir, output_dir, output_suffix):
    
    analysis_list = util.list_filetype_in_dir(sample_dir, '.csv')
    
    clean_dataframe = clean_up_dataframes(analysis_list)
    
    
        #Find the ROI string
        
    
    return

def bulk_write_roi_comparison_file():
    #For each sample
    #write roi comparison file
    return

def plot_roi_comparison():
    return

def r2_roi_comparison():
    return
