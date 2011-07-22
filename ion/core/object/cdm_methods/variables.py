#!/usr/bin/env python
"""
@file ion/core/object/cdm_methods/variables.py
@brief Wrapper methods for the cdm variable object
@author David Stuebe
@author Tim LaRocque
TODO: Implement get_intersecting...
"""

# Get the object decorator used on wrapper methods!
from ion.core.object.object_utils import _gpb_source


from ion.core.object.object_utils import OOIObjectError
import ion.util.ionlog
log = ion.util.ionlog.getLogger(__name__)

from ion.core.object.cdm_methods import group

from math import ceil

#--------------------------------------#
# Wrapper_Variable Specialized Methods #
#--------------------------------------#

@_gpb_source
def _get_var_units(self):
    """
    Specialized method for CDM Objects to retrieve the value of a variable object's 'units' attribute
    """
    result = None
    units = group._find_attribute_by_name(self, 'units')
    if units is not None and len(units.array.value) > 0:
        result = units.array.value[0]

    # @attention: Sometimes (string) attribute values come back as unicode values..  we can provide
    #             a trap here to convert them, but this may not be necessary.  Lets discuss [TPL]
    return result

@_gpb_source
def _get_var_std_name(self):
    """
    Specialized method for CDM Objects to retrieve the value of a variable object's 'standard_name' attribute
    """
    result = None
    name = group._find_attribute_by_name(self, 'standard_name')
    if name is not None and len(name.array.value) > 0:
        result = name.array.value[0]

    # @attention: Sometimes (string) attribute values come back as unicode values..  we can provide
    #             a trap here to convert them, but this may not be necessary.  Lets discuss [TPL]
    return result

@_gpb_source
def _get_var_num_dims(self):
    """
    Specialized method for CDM variables to retrieve its dimensionality
    """
    return len(self.shape)

@_gpb_source
def _get_var_num_ba(self):
    """
    Specialized method for CDM variables to retrieve the number of bounded arrays used in
    defining this variables content
    """
    return len(self.content.bounded_arrays)



@_gpb_source
def GetValue(self, *args):
    """
    @Brief Get a value from an array structure by its indices
    @param self - a cdm variable object
    @param args - a list of integer indices for the value to extract

    usage for a 3Dimensional variable:
    as.getValue(1,3,9)
    """
    
    # @todo: Need tests for multidim arrays
    # @todo: Check the rank outside the for loop
    # @todo: Check to make sure args are integers!

    value = None
    
    for ba in self.content.bounded_arrays:
    

        for index, bounds in zip(args, ba.bounds):
            if bounds.origin > index or index >= bounds.origin + bounds.size :
                break

        else:
            # We now have the the ndarray of interest..  extract the value!

            # Create a list of this bounded_array's sizes and use origin to determine
            # the given indices position in the ndarray
            indices = []
            shape = []
            for index, bounds in zip(args, ba.bounds):
                  indices.append(index - bounds.origin)  
                  shape.append(bounds.size)  
            
            # Find the flattened index (make sure to apply the origin values as an offset!)
            flattened_index = _flatten_index(indices, shape)
            
            # Grab the value from the ndarray
            value = ba.ndarray.value[flattened_index]
            break


    return value


@_gpb_source
def GetIntersectingBoundedArrays(self, bounded_array):
    """
    @brief get the SHA1 id of the bounded arrays which intersect the give coverage.
    @param self - a cdm variable object
    @param bounded_array - a bounded array which specifies an index space coverage of interest

    usage for a 3Dimensional variable:
    as.getValue(1,3,9)
    """

    # Get the MyId attribute of the bounded arrays that intersect - that will be the sha1 name for that BA...

    sha1_list = []
    return sha1_list


def _flatten_index(indices, shape):
    """
    Uses the given indices representing a position in a multidimensional context to determine the
    equivalent position in a flattened 1D array representation of that same nD context.  The
    cardinality (also size) of each dimension in multidimensional space is given by "shape".
    Note: This means that both "indices" and "shape" must be lists with the same rank (aka length.)
    """
    assert(isinstance(indices, list))
    assert(isinstance(shape, list))
    assert(len(indices) == len(shape))
    
    result = 0
    for i in range(len(indices)):
        offset = 1
        for j in range(i+1, len(shape)):
            offset *= shape[j]
        result += indices[i] * offset
    
    return result


def _unflatten_index(index, shape):
    """
    Uses the given storage-flattened index to produce its equivalent multidimentional position (indices)
    given the shape of the multidimensional space from which it was flattened.
    """
    assert(isinstance(index, int))
    assert(isinstance(shape, list))
    assert(len(shape) > 0)

    indices = []
    for x in range(len(shape)):
        # Determine the significance of this dimension
        sig = 1
        for i in range(x+1, len(shape)):
            sig *= shape[i]
        
        # Determine this dimension's index for the flattened array index:
        unflat = ceil(index / sig)
        if unflat >= shape[x]:
            unflat %= shape[x]

        indices.append(unflat)

    return indices


"""
#---------------------------
# Test a 1D dataset
#---------------------------
from ion.services.coi.datastore_bootstrap.ion_preload_config import SAMPLE_DLY_DISCHARGE_DATASET_ID
from ion.services.coi.resource_registry.resource_client import ResourceClient
rc = ResourceClient()
ds_d = rc.get_instance(SAMPLE_DLY_DISCHARGE_DATASET_ID)

ds = ds_d.result.ResourceObject
root = ds.root_group
flow = root.FindVariableByName('streamflow')


--------------------------------------------------------------------

from ion.core.object.cdm_methods.variables import GetValue
for i in range(flow.content.bounded_arrays[0].bounds[0].size):
    print GetValue(flow, i)


#---------------------------
# Test a 3D/4D dataset
#---------------------------
from ion.services.coi.datastore_bootstrap.ion_preload_config import SAMPLE_HYCOM_DATASET_ID
from ion.services.coi.resource_registry.resource_client import ResourceClient
rc = ResourceClient()
ds_headers_d = rc.get_instance(SAMPLE_HYCOM_DATASET_ID)

ds_slim = ds_headers_d.result.ResourceObject
ds_d = ds_slim.Repository.checkout('master', excluded_types=[])

ds = ds_d.result.resource_object
root = ds.root_group
ssh = root.FindVariableByName('ssh')
for dim in ssh.shape:
    print str(dim.name)


#--------------------------------------------------------------------

from ion.core.object.cdm_methods.variables import GetValue
count = 1
for bounds in ssh.content.bounded_arrays[0].bounds:
    count *= bounds.size 

# All values iterated by bounds
for i in range(ssh.content.bounded_arrays[0].bounds[0].size):
    for j in range(ssh.content.bounded_arrays[0].bounds[1].size):
        for k in range(ssh.content.bounded_arrays[0].bounds[2].size):
            print '(%03i,%03i,%03i) = %s' % (i, j, k, str(ssh.GetValue(i, j, k)))

# List a specific range of Sea Surface Height Values
i = 0
k = 174
for j in range(ssh.content.bounded_arrays[0].bounds[1].size):
    print '(%03i,%03i,%03i) = %s' % (i, j, k, str(ssh.GetValue(i, j, k)))

# List a vertical column of values for temperature
temp = root.FindVariableByName('layer_temperature')
depth = root.FindDimensionByName('Layer')
i = 0
k = 100
l = 200
for j in range(depth.length):
    print '(%03i,%03i,%03i,%03i) = %s' % (i, j, k, l, str(temp.GetValue(i, j, k, l)))



"""
