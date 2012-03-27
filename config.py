#!/Library/Frameworks/EPD64.framework/Versions/Current/bin/python
import os

FSLDIR= '/usr/local/fsl'
scripts_dir = '/Users/ranjeet.khanuja/Documents/workspace/GroupAnalysis/'
working_dir= '/Users/ranjeet.khanuja/Documents/workspace/GroupAnalysis/working_dir3/'
seed_file= os.path.abspath(scripts_dir + 'seed_list')
batch_file= os.path.abspath(scripts_dir +'batch_list')
subject_file=os.path.abspath(scripts_dir + 'subject.txt')
z_threshold = 2.3
p_threshold= 0.05
f_test='yes'

    
def readModels():
    
    fp = open(batch_file,'r')
    lines = fp.readline()
    fp.close()
     
    lines= lines.rstrip('/r/n')
    line1=lines.split()
    
    print line1
    base_dir= line1[0]
    model_file=line1[1]
    
    return base_dir, model_file
         

def processModels():
    
    modelist=[]
    seedlist=[]

    try:
        base_dir, model_file= readModels()
        fp = open(model_file,'r')
        models = fp.readlines()
        fp.close()

        for model in models:
            model = model.rstrip('\r\n')
            print 'inside processModels ; before check processed model ',model
            modelist.append(model)
    
                
        f= open(seed_file, 'r')
        seeds=f.readlines()
        f.close()
        
        for seed in seeds:
            seed = seed.rstrip('\r\n')
            print 'inside processModels ; checking for seeds ',seed
            seedlist.append(seed)
    except:
        raise
    print "seedlist :", seedlist
    return base_dir, modelist, seedlist

                
def create_dataflow(base_dir, modelist, seedlist, wfname= "datasource"):
    import nipype.pipeline.engine as pe
    import nipype.interfaces.io as nio
    
    #define your subject directory structure inside the base directory folder
    subject_dir='subjects/*/%s'
    
    datasource = pe.Node( interface = nio.DataGrabber(infields=['model_name','seed_list'], outfields = ['mat','con','fts','grp','seedfiles']) , name= 'datasource')
    datasource.inputs.base_directory = base_dir
    datasource.inputs.template= '*'
    datasource.inputs.field_template = dict(mat='models/%s/%s.mat',
                                        con='models/%s/%s.con',
                                        fts='models/%s/%s.fts',
                                        grp='models/%s/%s.grp',
                                        seedfiles=subject_dir)
    
    datasource.inputs.template_args = dict(mat=[['model_name', 'model_name']],
                                           con=[['model_name', 'model_name']],
                                           fts=[['model_name', 'model_name']],
                                           grp=[['model_name', 'model_name']],
                                           seedfiles=[['seed_list']])
    
    datasource.iterables = [('model_name',modelist),('seed_list',seedlist)]
    
    return datasource
    