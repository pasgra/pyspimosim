var ROOT_TO_PAGE              = '../';
var PAGE_TO_ROOT              = location.pathname.replace(/\/$/, '').replace(/^.*\//, '') + '/';

var LIB_SPIMOSIM_CORE_TO_ROOT = 'lib/spimosimCore/';
var ROOT_TO_LIB_SPIMOSIM_CORE = '../../';
var MODULES_TO_ROOT = 'lib/modules/';
var ROOT_TO_MODULES = '../../';
var LIB_SPIMOSIM_UI_TO_ROOT   = 'lib/spimosimUi/';
var ROOT_TO_LIB_SPIMOSIM_UI   = '../../';
var LIB_SPIMOSIM_NETWORK_TO_ROOT   = 'lib/spimosimNetwork/';
var ROOT_TO_LIB_SPIMOSIM_NETWORK   = '../../';
var LIB_GIF_TO_ROOT           = 'ext_lib/lib/gif.js/';

var modelConfig = {
    info: {
        title: "Python SpiMoSim backend – tech mode: Two Colomn CSV Model",
        url: ROOT_TO_PAGE + PAGE_TO_ROOT + 'model-info.html',
        helpTextId: 'custom',
        iconUrl: ROOT_TO_PAGE + LIB_SPIMOSIM_UI_TO_ROOT + 'icon/'
    },
    controls: {
        stateVariables: {
            x: {
                type: 'Float64',
                labelText: 'x',
                plot: {
                  description: 'x',
                  optionText: 'x'
                }
            },
            y: {
                type: 'Float64',
                labelText: 'y',
                plot: {
                  description: 'y',
                  optionText: 'y'
                }
            }
        },
        parameters: [],
        features: ["deleteOldData"]
    },
    simulation: {
        backend: {
            type: "server",
            url: wsAddress
        },
        continuableWithNewSettings: true
    },
    plotter: {
        features: true,
        backend: {
            type: 'webworker',
            workerUrl: ROOT_TO_PAGE + MODULES_TO_ROOT +
            'PlotBackend/webworker.worker.js',
            urls: [
                "../" + ROOT_TO_LIB_SPIMOSIM_CORE + MODULES_TO_ROOT + 'PlotComputer/mean-value.js',
                "../" + ROOT_TO_LIB_SPIMOSIM_CORE + MODULES_TO_ROOT + 'PlotComputer/auto-correlation.js',
                "../" + ROOT_TO_LIB_SPIMOSIM_CORE + MODULES_TO_ROOT + 'PlotComputer/distribution.js',
                "../" + ROOT_TO_LIB_SPIMOSIM_CORE + MODULES_TO_ROOT + 'PlotComputer/cumulated.js',
                "../" + ROOT_TO_LIB_SPIMOSIM_CORE + PAGE_TO_ROOT + 'plots/plot-computers.js'
            ]
        },
        plotTypes: [
        ],
        defaultPlots: [
            {"type": "x"},
            {"type": "y"}
        ]
    },
    video: {
        features: true,
        type: "dummy"
    },
    clock: {
        fps: {
            value: 40000,
            max: 400000
        }
    }
};
spimosimCore.modules.add('ModelConfig', "two_col_csv", modelConfig);
