"""Post-process DAG for annual daylight."""
from dataclasses import dataclass
from pollination_dsl.dag import Inputs, GroupedDAG, task, Outputs
from pollination.honeybee_radiance_postprocess.grid import MergeFolderMetrics


@dataclass
class AnnualDaylightPostProcess(GroupedDAG):
    """Post-process for annual daylight."""

    # inputs
    model = Inputs.file(
        description='Input Honeybee model.',
        extensions=['json', 'hbjson', 'pkl', 'hbpkl', 'zip']
    )

    initial_results = Inputs.folder(
        description='Folder with initial results. This is the distributed '
        'results.',
        path='initial_results'
    )

    dist_info = Inputs.file(
        description='Distribution information file.',
        path='dist_info.json'
    )

    grids_info = Inputs.file(
        description='Grid information file.',
        path='grids_info.json'
    )

    @task(
        template=MergeFolderMetrics,
        sub_paths={
            'input_folder': 'metrics'
        }
    )
    def restructure_metrics(
        self, input_folder=initial_results,
        dist_info=dist_info,
        grids_info=grids_info
    ):
        return [
            {
                'from': MergeFolderMetrics()._outputs.output_folder,
                'to': 'metrics'
            }
        ]

    metrics = Outputs.folder(
        source='metrics', description='metrics folder.'
    )
