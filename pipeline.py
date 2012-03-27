#!/Library/Frameworks/EPD64.framework/Versions/Current/bin/python
import sys
import os
import commands
import nipype.pipeline.engine as pe
import nipype.interfaces.fsl as fsl
import nipype.interfaces.io as nio
import nipype.interfaces.utility as util
from nipype.interfaces.fsl import MultiImageMaths
from multiprocessing import Process
from multiprocessing import Pool
from ConfigParser import SafeConfigParser
from config import *

#get pixdim3
def get_standard_background_img(in_file):
    import os
    
    from nibabel import load
    img= load(in_file)
    hdr = img.get_header()
    group_mm = int(hdr.get_zooms()[2])
    print "gorup_mm -> ", group_mm
    path='/usr/local/fsl' + '/data/standard/MNI152_T1_%smm_brain.nii.gz' %(group_mm)
    print "path ->", path
    return os.path.abspath(path)

#get dim3
def get_nvols(in_file):
    
    from nibabel import load 
    img = load(in_file)
    hdr = img.get_header()
    n_vol = int(hdr.get_data_shape()[3])
    op_string='-abs -bin -Tmean -mul %d' %(n_vol)
    return op_string

def copyGeom(infile_a, infile_b):
    import subprocess as sb
    out_file= infile_b
    cmd= sb.Popen(['fslcpgeom', infile_a, out_file], stdin=sb.PIPE, stdout= sb.PIPE,)
    stdout_value, stderr_value= cmd.communicate()
    return out_file

def getTuple(infile_a, infile_b):
    
    print "inisde getTuple"
    print "infile_a -> ",infile_a
    print "infile_b -> ",infile_b[1]
     
    return (infile_a,infile_b[1])

def create_group_analysis():
    
    grp_analysis=pe.Workflow(name= 'group_analysis')
    
    inputnode = pe.Node(util.IdentityInterface(fields=[ 'mat_file',
                                                        'con_file',
                                                        'fts_file',
                                                        'grp_file',
                                                        'seed_files',
                                                        'z_threshold',
                                                        'p_threshold']),
                         name='inputspec')
    
    inputnode_ftest = pe.Node(util.IdentityInterface(fields=['ftest']),
                             name='ftest_input')
     
    gp_fslmerge= pe.Node(interface=fsl.Merge(), name='gp_fslmerge')
    gp_fslmerge.inputs.dimension='t'
    
    gp_fslmaths=pe.Node(interface= fsl.ImageMaths(), name='gp_fslmaths')
    gp_fslmaths.inputs.op_string='-abs -Tmin -bin'
    
    gp_flameo= pe.Node(interface=fsl.FLAMEO(), name='gp_flameo')
    gp_flameo.inputs.run_mode='ols'
 
    
    gp_smooth_estimate= pe.MapNode (interface= fsl.SmoothEstimate(), name ='gp_smooth_estimate', iterfield= ["zstat_file"]) 
 
    gp_fslmultimaths=pe.MapNode( interface= fsl.MultiImageMaths(), name='gp_fslmultimaths', iterfield = ["in_file"])
    gp_fslmultimaths.inputs.op_string="-mas %s"
    
    gp_fslcpgeom= pe.MapNode(util.Function(input_names= ['infile_a', 'infile_b'], output_names= ['out_file'], function= copyGeom), name='gp_fslcpgeom',iterfield = ["infile_a","infile_b"])
 
    gp_cluster= pe.MapNode( interface= fsl.Cluster(), name= 'gp_cluster', iterfield = ["in_file","volume","dlh"])
    gp_cluster.inputs.out_index_file = True
    gp_cluster.inputs.out_threshold_file = True
    gp_cluster.inputs.out_localmax_txt_file = True
    gp_cluster.inputs.out_localmax_vol_file = True 
    gp_cluster.inputs.out_size_file = True 
    gp_cluster.inputs.out_max_file =True
    gp_cluster.inputs.out_mean_file= True
    gp_cluster.inputs.out_pval_file= True
    
    gp_fslstats = pe.MapNode(interface = fsl.ImageStats(), name = 'gp_fslstats', iterfield = ["in_file"])
    gp_fslstats.inputs.op_string='-R'
    
    gp_merge= pe.MapNode(util.Function(input_names= ['infile_a', 'infile_b'], output_names= ['out_file'], function= getTuple), name='gp_merge',iterfield = ["infile_b"])
    
    
    gp_overlay=pe.MapNode(interface=fsl.Overlay(), name='gp_overlay', iterfield=["stat_image","stat_thresh"])
    gp_overlay.inputs.transparency= True
    gp_overlay.inputs.auto_thresh_bg= True
    gp_overlay.inputs.out_type='float'
    
    
   
    gp_slicer= pe.MapNode(interface= fsl.Slicer(), name = 'gp_slicer', iterfield = ["in_file"])
    gp_slicer.inputs.image_width= 750
    gp_slicer.inputs.all_axial=True
    #gp_slicer.inputs.out_file=rendered_thresh_$6.png
    
    gp_fslmultimaths2=pe.Node(interface= fsl.ImageMaths(), name='gp_fslmaths2')
    #gp_fslmultimaths2.inputs.op_string='-abs -bin -Tmean -mul %d' 
    
    gp_nvols= pe.Node(util.Function(input_names= ['in_file'], output_names=['out_file'] , function = get_nvols), name='gp_nvols')
    gp_getbackgroundimage=pe.MapNode(util.Function(input_names= ['in_file'], output_names=['out_file'] , function = get_standard_background_img), name='gp_getbackgroundimage',iterfield = ["in_file"])
    
    grp_analysis.connect(inputnode,'seed_files', gp_fslmerge,'in_files')
    grp_analysis.connect(gp_fslmerge,'merged_file',gp_fslmaths,'in_file')
   
    #flameo= fsl.FLAMEO( cope_file ='zfstats/Sharad_test_VMHC_Z_stat_data.nii.gz', 
    #mask_file='zfstats/Sharad_test_VMHC_Z_stat_mask.nii.gz', design_file ='group_models/Sharad_test.mat', 
    #t_con_file='group_models/Sharad_test.con', cov_split_file='group_models/Sharad_test.grp', run_mode='ols')
    if f_test == 'yes' :
        grp_analysis.connect(gp_fslmerge,'merged_file', gp_flameo,'cope_file' )
        grp_analysis.connect(gp_fslmaths,'out_file', gp_flameo,'mask_file' )
        grp_analysis.connect(inputnode,'mat_file', gp_flameo,'design_file' )
        grp_analysis.connect(inputnode,'con_file', gp_flameo,'t_con_file' )
        grp_analysis.connect(inputnode,'grp_file', gp_flameo,'cov_split_file' )
        grp_analysis.connect(inputnode,'fts_file', gp_flameo, 'f_con_file' )
    else:
        grp_analysis.connect(gp_fslmerge,'merged_file', gp_flameo,'cope_file' )
        grp_analysis.connect(gp_fslmaths,'out_file', gp_flameo,'mask_file' )
        grp_analysis.connect(inputnode,'mat_file', gp_flameo,'design_file' )
        grp_analysis.connect(inputnode,'con_file', gp_flameo,'t_con_file' )
        grp_analysis.connect(inputnode,'grp_file', gp_flameo,'cov_split_file' )
    
    
    grp_analysis.connect(gp_flameo,'zstats', gp_smooth_estimate,'zstat_file' )
    grp_analysis.connect(gp_fslmaths,'out_file', gp_smooth_estimate,'mask_file' )
    
    grp_analysis.connect(gp_flameo, 'zstats',gp_fslmultimaths,'in_file')
    grp_analysis.connect(gp_fslmaths, 'out_file', gp_fslmultimaths,'operand_files')
    
    grp_analysis.connect(gp_fslmultimaths,'out_file', gp_getbackgroundimage,'in_file' )
    
    grp_analysis.connect(gp_getbackgroundimage,'out_file', gp_fslcpgeom, 'infile_a' )
    grp_analysis.connect(gp_fslmultimaths, 'out_file', gp_fslcpgeom, 'infile_b')
    
    #cluster -i thresh.nii.gz -t 2.3 -p 0.05 --volume=199540 -d 0.00024348 -o cluster_mask --othresh=thresh.nii.gz result >cluster_.txt
    #import nipype.interfaces.fsl as fsl
    #c1=fsl.Cluster()
    #c1.inputs.in_file= 'before_cluster_thresh.nii.gz'
    #c1.inputs.threshold=2.3
    #c1.inputs.pthreshold=0.05
    #c1.inputs.volume=199540
    # c1.inputs.dlh=0.00024348
    # c1.inputs.out_threshold_file= 'nipype_threshold.nii.gz'
    #c1.run()
    grp_analysis.connect(gp_fslcpgeom,'out_file',gp_cluster,'in_file')
    grp_analysis.connect(inputnode, 'z_threshold', gp_cluster,'threshold')
    grp_analysis.connect(inputnode,'p_threshold', gp_cluster, 'pthreshold')
    grp_analysis.connect(gp_smooth_estimate,'volume', gp_cluster,'volume')
    grp_analysis.connect(gp_smooth_estimate,'dlh', gp_cluster,'dlh')
    
    
    grp_analysis.connect(gp_cluster,'threshold_file',gp_fslstats,'in_file')
    
    grp_analysis.connect(gp_fslstats, 'out_stat', gp_merge, 'infile_b')
    grp_analysis.connect(inputnode, 'z_threshold', gp_merge, 'infile_a')
    
    grp_analysis.connect(gp_cluster,'threshold_file', gp_overlay,'stat_image')
    grp_analysis.connect(gp_merge,'out_file', gp_overlay,'stat_thresh')
    
    grp_analysis.connect(gp_fslmaths,('out_file', get_standard_background_img),  gp_overlay,'background_image')
    
    grp_analysis.connect(gp_overlay,'out_file', gp_slicer,'in_file')
    
    grp_analysis.connect(gp_fslmerge,'merged_file',gp_nvols,'in_file')
    grp_analysis.connect(gp_fslmerge,'merged_file',gp_fslmultimaths2,'in_file' )
    grp_analysis.connect(gp_nvols,'out_file', gp_fslmultimaths2,'op_string')
    
    outputnode = pe.Node(util.IdentityInterface(fields=['merged',
                                                        'math_mask',
                                                        'zstats',
                                                        'multi_math_mask',
                                                        'orig_threshold',
                                                        'volume',
                                                        'degree_of_freedom',
                                                        'cluster_threshold',
                                                        'cluster_localmax',
                                                        'cluster_index',
                                                        'combined_image_volume',
                                                        'min_max_thresh',
                                                        'picture',
                                                        'multi_math_mask2' ]),
                         name='outputspec')
   
   
    grp_analysis.connect(gp_fslmerge,'merged_file', outputnode,'merged')
    grp_analysis.connect(gp_fslmaths,'out_file', outputnode,'math_mask')
    grp_analysis.connect(gp_flameo,'zstats', outputnode,'zstats')
    grp_analysis.connect(gp_fslmultimaths,'out_file',outputnode,'multi_math_mask')
    grp_analysis.connect(gp_fslcpgeom,'out_file',outputnode, 'orig_threshold')
    grp_analysis.connect(gp_smooth_estimate,'volume', outputnode, 'volume')
    grp_analysis.connect(gp_smooth_estimate,'dlh', outputnode, 'degree_of_freedom')
    grp_analysis.connect(gp_cluster,'threshold_file', outputnode, 'cluster_threshold')
    grp_analysis.connect(gp_cluster,'localmax_txt_file', outputnode, 'cluster_localmax')
    grp_analysis.connect(gp_cluster,'index_file', outputnode, 'cluster_index')
    grp_analysis.connect(gp_overlay,'out_file', outputnode, 'combined_image_volume')
    grp_analysis.connect(gp_merge,'out_file', outputnode, 'min_max_thresh')
    grp_analysis.connect(gp_slicer,'out_file', outputnode, 'picture')
    grp_analysis.connect(gp_fslmultimaths2,'out_file', outputnode,'multi_math_mask2')
    
    return grp_analysis


def main_workflow(base_dir, modelist, seedlist):
    
    mainflow= pe.Workflow(name= 'analysis')
    mainflow.base_dir = working_dir
    dataflow= create_dataflow(base_dir,modelist,seedlist)
    
    preproc= create_group_analysis()
    
    preproc.inputs.inputspec.z_threshold= z_threshold
    preproc.inputs.inputspec.p_threshold= p_threshold
    
    mainflow.connect(dataflow,'mat', preproc,'inputspec.mat_file')
    mainflow.connect(dataflow,'con', preproc,'inputspec.con_file')
    mainflow.connect(dataflow,'grp', preproc,'inputspec.grp_file')
    mainflow.connect(dataflow,'fts', preproc,'inputspec.fts_file')
    mainflow.connect(dataflow,'seedfiles', preproc,'inputspec.seed_files')
    
    return mainflow
   
def main():

    if ( len(sys.argv) < 2 ):
        sys.stderr.write("./pipeline.py <Number_of_cores>")
    else:
        numCores=int(sys.argv[1])
        base_dir, modelist, seedlist= processModels()
        print "lenghts -> ", len(modelist), len(seedlist)
        if len(modelist)>0 and len(seedlist)>0:
            preprocess = main_workflow(base_dir, modelist,seedlist)
            print "created workflow"
            preprocess.run(plugin='MultiProc', plugin_args={'n_procs' : numCores})
        else:
            print "model list or seedlist is empty"

    

if __name__ == "__main__":

    sys.exit(main())
    