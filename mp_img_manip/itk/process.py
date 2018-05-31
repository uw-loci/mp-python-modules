# -*- coding: utf-8 -*-
"""
Created on Wed Mar 21 10:06:55 2018

@author: mpinkert
"""
import mp_img_manip.bulk_img_processing as blk
import mp_img_manip.utility_functions as util
import mp_img_manip.itk.metadata as meta
import mp_img_manip.plotting as myplot

import SimpleITK as sitk
import numpy as np
import os

def overlay_images(fixed_image, moving_image, alpha = 0.7):
    """Create a numpy array that is a combination of two images
    
    Inputs:
    fixed_image -- Image one, using registration nomenclature
    moving_image -- Image two, using registration nomeclature
    alpha -- degree of weighting towards the moving image
    
    Output:
    combined_array -- A numpy array of overlaid images
    """
    
    fixed_array = sitk.GetArrayFromImage(fixed_image)
    fixed_normalized = (fixed_array - np.amin(fixed_array))/(
            np.amax(fixed_array) + np.amin(fixed_array))

    try: #Post-registration
        moving_array = sitk.GetArrayFromImage(moving_image)
        moving_normalized = (moving_array - np.amin(moving_array))/(
                np.amax(moving_array)+np.amin(moving_array))
        
#        combined_array = ((1.0 - alpha)*fixed_normalized 
#                          + alpha*moving_normalized)
        
        combined_array = myplot.plot_colored_overlay(
                fixed_normalized, moving_normalized)
        
        return combined_array
    
    except: #Pre-registration
        initial_transform = sitk.Similarity2DTransform()
        moving_resampled = sitk.Resample(moving_image, fixed_image, 
                                         initial_transform, sitk.sitkLinear,
                                         0.0, moving_image.GetPixelID())
        
        moving_array = sitk.GetArrayFromImage(moving_resampled)
        moving_normalized = (moving_array - np.amin(moving_array))/(
                np.amax(moving_array)+np.amin(moving_array))

#        combined_array = ((1.0 - alpha)*fixed_normalized 
#                          + alpha*moving_normalized)
#        
        combined_array = myplot.plot_colored_overlay(
                fixed_normalized, moving_normalized)
                
        return combined_array    
    

def bulk_apply_mask(image_dir, mask_dir,
                    output_dir, output_suffix):
    """Find corresponding images between dirs and apply the second as a mask
    
    Inputs:
    image_dir -- Directory of images to-be-masked
    mask_dir -- Directory of images that will be used as the mask
    output_dir -- Directory where the masked images will be saved
    ouptut_suffix -- Filename text after the core/sample name of the image file
    """
    
    
    (image_path_list, mask_path_list) = blk.find_shared_images(
            image_dir, mask_dir)
    
    for i in range(np.size(image_path_list)):
        
        image = meta.setup_image(image_path_list[i])
        mask = meta.setup_image(mask_path_list[i]) > 0
        
        print('Masking ' + os.path.basename(image_path_list[i]) + ' with '
          + os.path.basename(mask_path_list[i]))
        
        masked_image = sitk.Mask(image,mask)
        
        masked_path = blk.create_new_image_path(
                image_path_list[i], output_dir, output_suffix)
        
        meta.write_image_parameters(masked_path,
                                    image.GetSpacing(),
                                    image.GetOrigin())
        sitk.WriteImage(masked_image, str(masked_path))
                
    
    
def threshold(itk_image, image_name, 
              threshold=1, unit='degree'):
    """Apply an intensity based threshold to an image"""
    print('Thresholding {0} to {1} {2}'.format(image_name, threshold, unit))
    
    mask = itk_image > threshold
    thresh_image = sitk.Mask(itk_image, mask)
    
    return thresh_image


def bulk_threshold(input_dir, output_dir, output_suffix):
    """Apply intensity based thresholds to all images in folder"""
    path_list = util.list_filetype_in_dir(input_dir, '.tif')
    
    for i in range(len(path_list)):
        original = meta.setup_image(path_list[i])
        new_image = threshold(original, 
                              os.path.basename(path_list[i]))
        
        new_path = blk.create_new_image_path(path_list[i],
                                             output_dir, output_suffix)
    
        meta.write_image_parameters(new_path, 
                                    original.GetSpacing(),
                                    original.GetOrigin())
        
        sitk.WriteImage(new_image, str(new_path))
    
    
def convert_to_eightbit(itk_image, image_name):
    """Convert an itk image to 8 bit integer pixels"""
    
    print('Converting {0} to 8-bit grayscale'.format(image_name))
    return sitk.Cast(sitk.RescaleIntensity(itk_image),
                               sitk.sitkUInt8)

    
def bulk_convert_to_eightbit(input_dir, output_dir, output_suffix):
    """Convert all tif images in a directory to 8bit and save in new directory
    
    Inputs:
    input_dir -- Directory of images to convert
    output_dir -- Directory to save converted images
    output_suffix -- Text in output image name after the core/sample name
    
    """
    
    path_list = util.list_filetype_in_dir(input_dir, '.tif')
    
    for i in range(len(path_list)):
        original = meta.setup_image(path_list[i])
        new_image = convert_to_eightbit(original, 
                                        os.path.basename(path_list[i]))
        
        new_path = blk.create_new_image_path(path_list[i],
                                             output_dir, output_suffix)
    
        meta.write_image_parameters(new_path, 
                                    original.GetSpacing(),
                                    original.GetOrigin())
        
        sitk.WriteImage(new_image, str(new_path))