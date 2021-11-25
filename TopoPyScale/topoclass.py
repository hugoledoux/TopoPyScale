'''
Toposcale class definition
S. Filhol, September 2021

project/
    config.ini
    -> input/
        -> dem/
        -> met_forcing/
    -> output/

'''
import os
#import configparser
import sys

from configobj import ConfigObj
import matplotlib.pyplot as plt
from TopoPyScale import fetch_era5 as fe
from TopoPyScale import topo_param as tp
from TopoPyScale import topo_sub as ts
from TopoPyScale import fetch_dem as fd
from TopoPyScale import solar_geom as sg
from TopoPyScale import topo_scale as ta


class Topoclass(object):
    
    def __init__(self, config_file):
        
        self.config = self.Config(config_file)
        self.toposub = self.Toposub()

        self.solar_ds = None
        self.horizon_da = None

        # add here a little routinr doing chek on start and end date in config.ini compare to forcing in case

        if not os.path.isfile(self.config.dem_path):
            fd.fetch_dem(self.config.project_dir, self.config.extent, self.config.dem_file)
        else:
            print('\n---> DEM file found')
            self.toposub.dem_path = self.config.dem_path

        # little routine checking that the DEM extent is within the climate extent
        if not self.check_extent_overlap():
            sys.exit()

        if self.config.forcing_dataset.lower() == 'era5':
            self.get_era5()

    class Toposub:
        '''
        Class to initialize variables to store TopoSub variables
        '''
        def __init__(self):
            self.dem_path = None
            self.df_param = None
            self.df_centroids = None
            self.kmeans_obj = None
            self.scaler = None

        def plot_clusters_map(self, var='cluster_labels', cmap=plt.cm.hsv, figsize=(14, 10)):
            ts.plot_center_clusters(self.dem_path, self.df_param, self.df_centroids, var=var, cmap=cmap, figsize=figsize)

    def check_extent_overlap(self):
        '''
        Function to check if the DEM spatial extent is within the climate data spatial extent
        :return: boolean, True if DEM is included within climate data
        '''
        dem_extent = tp.get_extent_latlon(self.config.dem_file, self.config.dem_epsg)
        print('---> Checking DEM and Climate data extent compatibilities')
        if (dem_extent.get('latN') > self.config.extent.get('latN')) or\
                (dem_extent.get('latS') < self.config.extent.get('latS')) or \
                (dem_extent.get('lonW') < self.config.extent.get('lonW')) or \
                (dem_extent.get('lonE') > self.config.extent.get('lonE')):
            print('ERROR: DEM extent falls outside of the climate data extent. \nVerify lat/lon in config file')
            return False
        else:
            print('OK')
            return True

    def compute_dem_param(self):
        self.toposub.df_param = tp.compute_dem_param(self.config.dem_path)

    def extract_pts_param(self, df, method=None):
        '''
        Function to use a list point as input rather than cluster centroids from DEM segmentation (topo_sub.py/self.clustering_dem()).
        :param df: pandas DataFrame
        :return:
        '''
        if method is None:
            method = self.config.pt_sampling_method

        if method == 'nearest':
            print('TBI')
            # sample methods: nearest, inverse



            #return self.toposub.df_centroids

    def extract_dem_cluster_param(self):
        '''
        Function to segment a DEM in clusters and retain only the centroids of each cluster.
        :return:
        '''
        df_scaled, self.toposub.scaler = ts.scale_df(self.toposub.df_param)
        if self.config.clustering_method.lower() == 'kmean':
            self.toposub.df_centroids, self.toposub.kmeans_obj, self.toposub.df_param['cluster_labels'] = ts.kmeans_clustering(df_scaled, self.config.n_clusters, seed=self.config.random_seed)
        elif self.config.clustering_method.lower() == 'minibatchkmean':
            self.toposub.df_centroids, self.toposub.kmeans_obj, self.toposub.df_param['cluster_labels'] = ts.minibatch_kmeans_clustering(df_scaled, self.config.n_clusters, self.config.n_cores,  seed=self.config.random_seed)
        else:
            print('ERROR: {} clustering method not available'.format(self.config.clustering_method))
        self.toposub.df_centroids = ts.inverse_scale_df(self.toposub.df_centroids, self.toposub.scaler)

    def compute_solar_geometry(self):
        self.solar_ds = sg.get_solar_geom(self.toposub.df_centroids,
                                          self.config.start_date,
                                          self.config.end_date,
                                          self.config.time_step,
                                          self.config.dem_epsg)

    def compute_horizon(self):
        '''
        Function to compute horizon angle and sample values for list of points
        :return:
        '''
        self.horizon_da = tp.compute_horizon(self.config.dem_path, self.config.horizon_az_inc)
        tgt_x = tp.xr.DataArray(self.toposub.df_centroids.x.values, dims="points")
        tgt_y = tp.xr.DataArray(self.toposub.df_centroids.y.values, dims="points")
        for az in self.horizon_da.azimuth.values:
            self.toposub.df_centroids['hori_azi_'+str(az)] = self.horizon_da.sel(x=tgt_x,
                                                                            y=tgt_y,
                                                                            azimuth=az,
                                                                            method='nearest').values.flatten()

    def downscale_climate(self):
        self.down_pts = ta.downscale_climate(self.config.forcing_path,
                                        self.toposub.df_centroids,
                                        self.solar_ds,
                                        self.horizon_da,
                                        self.config.dem_epsg)

    class Config:
        '''
        Class to contain all config.ini parameters
        '''
        def __init__(self, config_file):
            self.file_config = config_file 
            
            # parse configuration file into config class
            self._parse_config_file()
            
            # check if tree directory exists. If not create it
            if not os.path.exists('/'.join((self.project_dir, 'inputs/'))):
                os.makedirs('/'.join((self.project_dir, 'inputs/')))
            if not os.path.exists('/'.join((self.project_dir, 'inputs/forcings/'))):
                os.makedirs('/'.join((self.project_dir, 'inputs/forcings')))
            if not os.path.exists('/'.join((self.project_dir, 'inputs/dem/'))):
                os.makedirs('/'.join((self.project_dir, 'inputs/dem/')))
            if not os.path.exists('/'.join((self.project_dir, 'outputs/'))):
                os.makedirs('/'.join((self.project_dir, 'outputs/')))
                
        def _parse_config_file(self):
            '''
            Function to parse config file .ini into a python class
            '''
            try:
                conf = ConfigObj(self.file_config)
            except IOError:
                print('ERROR: config file does not exist. Check path.')

            self.project_dir = conf['main']['project_dir']
            self.project_description = conf['main']['project_description']
            self.project_name = conf['main']['project_name']
            self.project_author = conf['main']['project_authors']
            
            self.start_date = conf['main']['start_date']
            self.end_date = conf['main']['end_date']
            self.extent = {'latN': conf['main'].as_float('latN'),
                           'latS': conf['main'].as_float('latS'),
                           'lonW': conf['main'].as_float('lonW'),
                           'lonE': conf['main'].as_float('lonE')}
            
            self.forcing_dataset = conf['forcing'].get('dataset')
            if self.forcing_dataset.lower() == 'era5':
                self.forcing_era5_product = conf['forcing']['era5_product']
                self.forcing_n_threads = conf['forcing'].as_int('n_threads_download')
            self.n_cores = conf['forcing'].as_int('n_cores')
            self.forcing_path = self.project_dir + 'inputs/forcings/'
                
            self.time_step = conf['forcing']['time_step']
            self.plevels = conf['forcing']['plevels']
            
            self.dem_file = conf['forcing'].get('dem_file')
            self.dem_epsg = conf['forcing'].get('dem_epsg')
            self.dem_path = self.project_dir + 'inputs/dem/' + self.dem_file
            self.horizon_az_inc = conf['forcing'].as_int('horizon_az_inc')

            self.n_clusters = conf['toposcale'].as_int('n_clusters')
            self.random_seed = conf['toposcale'].as_int('random_seed')
            self.clustering_method = conf['toposcale']['clustering_method']
            self.interp_method = conf['toposcale']['interpolation_method']
            self.pt_sampling_method = conf['toposcale']['pt_sampling_method']
            
    def get_era5(self):
        '''
        Funtion to call fetching of ERA5 data
        TODO:
        - merge monthly data into one file (cdo?)
        '''
        lonW = self.config.extent.get('lonW') - 0.25
        lonE = self.config.extent.get('lonE') + 0.25
        latN = self.config.extent.get('latN') + 0.25
        latS = self.config.extent.get('latS') - 0.25

        # retreive ERA5 surface data
        fe.retrieve_era5(
            self.config.forcing_era5_product,
            self.config.start_date,
            self.config.end_date,
            self.config.forcing_path,
            latN, latS, lonE, lonW,
            self.config.time_step,
            self.config.forcing_n_threads,
            surf_plev='surf'
            )
        # retrieve era5 plevels
        fe.retrieve_era5(
            self.config.forcing_era5_product,
            self.config.start_date,
            self.config.end_date,
            self.config.forcing_path,
            latN, latS, lonE, lonW, 
            self.config.time_step,
            self.config.forcing_n_threads,
            surf_plev='plev',
            plevels=self.config.plevels,
            )
            

    
    def to_cryogrid(self):
        '''
        function to export toposcale output to cryosgrid format .mat
        '''
        
    def to_fsm(self):
        '''
        function to export toposcale output to FSM format
        '''
        
    def to_crocus(self):
        '''
        function to export toposcale output to crocus format .nc
        '''

    
    def to_snowmodel(self):
        '''
        function to export toposcale output to snowmodel format .ascii, for single station standard
        '''
    
    def to_netcdf(self, file_out='./outputs/output.nc'):
        '''
        function to export toposcale output to generic netcdf format
        '''
        self.down_pts.to_netcdf(file_out)