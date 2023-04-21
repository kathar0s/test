"""
Model exported as python.
Name : 2) extract shadow points
Group : 
With QGIS : 32002
"""

from qgis.core import QgsProcessing
from qgis.core import QgsProcessingAlgorithm
from qgis.core import QgsProcessingMultiStepFeedback
from qgis.core import QgsProcessingParameterNumber
from qgis.core import QgsProcessingParameterString
from qgis.core import QgsProcessingParameterVectorLayer
from qgis.core import QgsProcessingParameterFeatureSink
from qgis.core import QgsExpression
from qgis.core import QgsProperty
import processing


class ExtractShadowPoints(QgsProcessingAlgorithm):

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterNumber('Altitude', 'Sun Altitude', type=QgsProcessingParameterNumber.Double, minValue=-1.79769e+308, maxValue=1.79769e+308, defaultValue=None))
        self.addParameter(QgsProcessingParameterString('BDMGTSN', 'BD_MGT_SN', multiLine=False, defaultValue=''))
        self.addParameter(QgsProcessingParameterString('Dates', 'Dates', multiLine=False, defaultValue=''))
        self.addParameter(QgsProcessingParameterNumber('sunazimuth', 'Sun Azimuth', type=QgsProcessingParameterNumber.Double, minValue=-1.79769e+308, maxValue=1.79769e+308, defaultValue=None))
        self.addParameter(QgsProcessingParameterVectorLayer('target', '1) target points', types=[QgsProcessing.TypeVectorPoint], defaultValue=None))
        self.addParameter(QgsProcessingParameterVectorLayer('targetpolygon', 'target polygon', types=[QgsProcessing.TypeVectorPolygon], defaultValue=None))
        self.addParameter(QgsProcessingParameterFeatureSink('Shaingpoint', 'Shaingpoint', type=QgsProcessing.TypeVectorAnyGeometry, createByDefault=True, supportsAppend=True, defaultValue=None))

    def processAlgorithm(self, parameters, context, model_feedback):
        # Use a multi-step feedback, so that individual child algorithm progress reports are adjusted for the
        # overall progress through the model
        feedback = QgsProcessingMultiStepFeedback(30, model_feedback)
        results = {}
        outputs = {}

        # Extract by polygon
        alg_params = {
            'FIELD': 'BD_MGT_SN',
            'INPUT': parameters['targetpolygon'],
            'OPERATOR': 0,  # =
            'VALUE': parameters['BDMGTSN'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['ExtractByPolygon'] = processing.run('native:extractbyattribute', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(1)
        if feedback.isCanceled():
            return {}

        # Translate shadow
        alg_params = {
            'DELTA_M': 0,
            'DELTA_X': QgsExpression('-0.05* sin( @sunazimuth * pi()/180)').evaluate(),
            'DELTA_Y': QgsExpression('-0.05* cos( @sunazimuth * pi()/180)').evaluate(),
            'DELTA_Z': 0,
            'INPUT': outputs['ExtractByPolygon']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['TranslateShadow'] = processing.run('native:translategeometry', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(2)
        if feedback.isCanceled():
            return {}

        # Translate points+
        alg_params = {
            'DELTA_M': 0,
            'DELTA_X': QgsExpression('500* sin( @sunazimuth * pi()/180)').evaluate(),
            'DELTA_Y': QgsExpression('500* cos( @sunazimuth * pi()/180)').evaluate(),
            'DELTA_Z': 0,
            'INPUT': outputs['ExtractByPolygon']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['TranslatePoints'] = processing.run('native:translategeometry', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(3)
        if feedback.isCanceled():
            return {}

        # Merge shadow layers
        alg_params = {
            'CRS': None,
            'LAYERS': [outputs['ExtractByPolygon']['OUTPUT'],outputs['TranslateShadow']['OUTPUT']],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['MergeShadowLayers'] = processing.run('native:mergevectorlayers', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(4)
        if feedback.isCanceled():
            return {}

        # Minimum bounding geometry
        alg_params = {
            'FIELD': 'BD_MGT_SN',
            'INPUT': outputs['MergeShadowLayers']['OUTPUT'],
            'TYPE': 3,  # Convex Hull
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['MinimumBoundingGeometry'] = processing.run('qgis:minimumboundinggeometry', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(5)
        if feedback.isCanceled():
            return {}

        # Difference
        alg_params = {
            'INPUT': outputs['MinimumBoundingGeometry']['OUTPUT'],
            'OVERLAY': parameters['targetpolygon'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['Difference'] = processing.run('native:difference', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(6)
        if feedback.isCanceled():
            return {}

        # Merge vector layers
        alg_params = {
            'CRS': None,
            'LAYERS': [outputs['ExtractByPolygon']['OUTPUT'],outputs['TranslatePoints']['OUTPUT']],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['MergeVectorLayers'] = processing.run('native:mergevectorlayers', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(7)
        if feedback.isCanceled():
            return {}

        # Minimum bounding geometry
        alg_params = {
            'FIELD': 'BD_MGT_SN',
            'INPUT': outputs['MergeVectorLayers']['OUTPUT'],
            'TYPE': 3,  # Convex Hull
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['MinimumBoundingGeometry'] = processing.run('qgis:minimumboundinggeometry', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(8)
        if feedback.isCanceled():
            return {}

        # Buffer
        alg_params = {
            'DISSOLVE': False,
            'DISTANCE': 0.0005,
            'END_CAP_STYLE': 0,  # Round
            'INPUT': outputs['Difference']['OUTPUT'],
            'JOIN_STYLE': 0,  # Round
            'MITER_LIMIT': 2,
            'SEGMENTS': 5,
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['Buffer'] = processing.run('native:buffer', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(9)
        if feedback.isCanceled():
            return {}

        # Extract by not shading
        alg_params = {
            'INPUT': parameters['target'],
            'INTERSECT': outputs['Buffer']['OUTPUT'],
            'PREDICATE': [2],  # disjoint
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['ExtractByNotShading'] = processing.run('native:extractbylocation', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(10)
        if feedback.isCanceled():
            return {}

        # 그림자생길수있는방향추출
        alg_params = {
            'INPUT': parameters['targetpolygon'],
            'INTERSECT': outputs['MinimumBoundingGeometry']['OUTPUT'],
            'PREDICATE': [0],  # intersect
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs[''] = processing.run('native:extractbylocation', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(11)
        if feedback.isCanceled():
            return {}

        # Extract by shading1
        alg_params = {
            'INPUT': parameters['target'],
            'INTERSECT': outputs['Buffer']['OUTPUT'],
            'PREDICATE': [0],  # intersect
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['ExtractByShading1'] = processing.run('native:extractbylocation', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(12)
        if feedback.isCanceled():
            return {}

        # Extract vertices
        alg_params = {
            'INPUT': outputs['']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['ExtractVertices'] = processing.run('native:extractvertices', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(13)
        if feedback.isCanceled():
            return {}

        # add ID2
        alg_params = {
            'FIELD_LENGTH': 10,
            'FIELD_NAME': 'ID2',
            'FIELD_PRECISION': 0,
            'FIELD_TYPE': 1,  # Integer
            'FORMULA': '1',
            'INPUT': outputs['ExtractByShading1']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['AddId2'] = processing.run('native:fieldcalculator', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(14)
        if feedback.isCanceled():
            return {}

        # Extract by expression
        alg_params = {
            'EXPRESSION': 'vertex_index is not 0',
            'INPUT': outputs['ExtractVertices']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['ExtractByExpression'] = processing.run('native:extractbyexpression', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(15)
        if feedback.isCanceled():
            return {}

        # Extract by expression
        alg_params = {
            'EXPRESSION': 'BD_MGT_SN is not  @BDMGTSN',
            'INPUT': outputs['ExtractByExpression']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['ExtractByExpression'] = processing.run('native:extractbyexpression', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(16)
        if feedback.isCanceled():
            return {}

        # Buffer
        alg_params = {
            'DISSOLVE': False,
            'DISTANCE': QgsProperty.fromExpression('height /tan( @Altitude *pi()/180)'),
            'END_CAP_STYLE': 0,  # Round
            'INPUT': outputs['ExtractByExpression']['OUTPUT'],
            'JOIN_STYLE': 0,  # Round
            'MITER_LIMIT': 2,
            'SEGMENTS': 5,
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['Buffer'] = processing.run('native:buffer', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(17)
        if feedback.isCanceled():
            return {}

        # Extract by location
        alg_params = {
            'INPUT': outputs['Buffer']['OUTPUT'],
            'INTERSECT': parameters['target'],
            'PREDICATE': [0],  # intersect
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['ExtractByLocation'] = processing.run('native:extractbylocation', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(18)
        if feedback.isCanceled():
            return {}

        # Centroids
        alg_params = {
            'ALL_PARTS': False,
            'INPUT': outputs['ExtractByLocation']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['Centroids'] = processing.run('native:centroids', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(19)
        if feedback.isCanceled():
            return {}

        # Drop field(s)
        alg_params = {
            'COLUMN': ['xcoord','ycoord','index','vertex_index','vertex_part','vertex_part_ring','vertex_part_index','distance','angle'],
            'INPUT': outputs['Centroids']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['DropFields'] = processing.run('native:deletecolumn', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(20)
        if feedback.isCanceled():
            return {}

        # Field calculator
        alg_params = {
            'FIELD_LENGTH': 10,
            'FIELD_NAME': 'feature',
            'FIELD_PRECISION': 0,
            'FIELD_TYPE': 0,  # Float
            'FORMULA': '@row_number',
            'INPUT': outputs['DropFields']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['FieldCalculator'] = processing.run('native:fieldcalculator', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(21)
        if feedback.isCanceled():
            return {}

        # Distance matrix
        alg_params = {
            'INPUT': outputs['ExtractByNotShading']['OUTPUT'],
            'INPUT_FIELD': 'feature',
            'MATRIX_TYPE': 0,  # Linear (N*k x 3) distance matrix
            'NEAREST_POINTS': 0,
            'TARGET': outputs['FieldCalculator']['OUTPUT'],
            'TARGET_FIELD': 'height',
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['DistanceMatrix'] = processing.run('qgis:distancematrix', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(22)
        if feedback.isCanceled():
            return {}

        # adds height to DTMT
        alg_params = {
            'DISCARD_NONMATCHING': False,
            'FIELD': 'InputID',
            'FIELDS_TO_COPY': ['height'],
            'FIELD_2': 'feature',
            'INPUT': outputs['DistanceMatrix']['OUTPUT'],
            'INPUT_2': parameters['target'],
            'METHOD': 1,  # Take attributes of the first matching feature only (one-to-one)
            'PREFIX': '',
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['AddsHeightToDtmt'] = processing.run('native:joinattributestable', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(23)
        if feedback.isCanceled():
            return {}

        # extract shading2
        alg_params = {
            'EXPRESSION': 'distance + height/tan( @Altitude  *pi()/180)<=TargetID/tan( @Altitude *pi()/180)',
            'INPUT': outputs['AddsHeightToDtmt']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['ExtractShading2'] = processing.run('native:extractbyexpression', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(24)
        if feedback.isCanceled():
            return {}

        # Join attributes by field value
        alg_params = {
            'DISCARD_NONMATCHING': False,
            'FIELD': 'feature',
            'FIELDS_TO_COPY': ['TargetID'],
            'FIELD_2': 'InputID',
            'INPUT': parameters['target'],
            'INPUT_2': outputs['ExtractShading2']['OUTPUT'],
            'METHOD': 1,  # Take attributes of the first matching feature only (one-to-one)
            'PREFIX': '',
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['JoinAttributesByFieldValue'] = processing.run('native:joinattributestable', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(25)
        if feedback.isCanceled():
            return {}

        # Results
        alg_params = {
            'DISCARD_NONMATCHING': False,
            'FIELD': 'feature',
            'FIELDS_TO_COPY': ['ID2'],
            'FIELD_2': 'feature',
            'INPUT': outputs['JoinAttributesByFieldValue']['OUTPUT'],
            'INPUT_2': outputs['AddId2']['OUTPUT'],
            'METHOD': 1,  # Take attributes of the first matching feature only (one-to-one)
            'PREFIX': '',
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['Results'] = processing.run('native:joinattributestable', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(26)
        if feedback.isCanceled():
            return {}

        # Final result
        alg_params = {
            'FIELD_LENGTH': 1,
            'FIELD_NAME': 'shading',
            'FIELD_PRECISION': 0,
            'FIELD_TYPE': 0,  # Float
            'FORMULA': 'if(TargetID is not NULL OR ID2 is not NULL, 1, 0)',
            'INPUT': outputs['Results']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['FinalResult'] = processing.run('native:fieldcalculator', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(27)
        if feedback.isCanceled():
            return {}

        # Drop field(s)
        alg_params = {
            'COLUMN': ['height','feature','TargetID','ID2'],
            'INPUT': outputs['FinalResult']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['DropFields'] = processing.run('native:deletecolumn', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(28)
        if feedback.isCanceled():
            return {}

        # Field calculator
        alg_params = {
            'FIELD_LENGTH': 0,
            'FIELD_NAME': 'Dates',
            'FIELD_PRECISION': 0,
            'FIELD_TYPE': 2,  # String
            'FORMULA': '\'20\'+@Dates',
            'INPUT': outputs['DropFields']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['FieldCalculator'] = processing.run('native:fieldcalculator', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(29)
        if feedback.isCanceled():
            return {}

        # Field calculator
        alg_params = {
            'FIELD_LENGTH': 0,
            'FIELD_NAME': 'index',
            'FIELD_PRECISION': 0,
            'FIELD_TYPE': 1,  # Integer
            'FORMULA': '\"index\"',
            'INPUT': outputs['FieldCalculator']['OUTPUT'],
            'OUTPUT': parameters['Shaingpoint']
        }
        outputs['FieldCalculator'] = processing.run('native:fieldcalculator', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
        results['Shaingpoint'] = outputs['FieldCalculator']['OUTPUT']
        return results

    def name(self):
        return '2) extract shadow points'

    def displayName(self):
        return '2) extract shadow points'

    def group(self):
        return ''

    def groupId(self):
        return ''

    def createInstance(self):
        return ExtractShadowPoints()
