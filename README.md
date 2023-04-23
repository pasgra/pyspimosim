# A python backend for SpiMoSim

[https://github.com/pasgra/spimosim](SpiMoSim) can provide a user interface to
models written in javascript that run directly in the browser or communicate
with a server that runs the model as implemented in this repository.

## Example: Ising Model

`models/ising_model.py` contains an example implementation of the Ising model
in python. `www/ising` contains model specific static files that are
directly served by a webserver. The data produced the Ising model
implemented in python is send via a websocket to the browser and shown in the
browser as a "video" with "up" and "down" spins on a 2D lattice. A plot shows
the ratio of "up" and "down" spins, also called "magnetisation".

### How to use

Start the python backend (this starts a webserver for serving files
and a websocket server to communicate with the simulation):

`> python3 -m pyspimosim ising-model`

*or*

`> python3 models/ising_model.py` 

Both do the same.

Open `http://localhost:8080/` in your browser or the address printed by
the command above. 

Different command line flags exist for ports, etc. Run

`> python3 -m pyspimosim --help`

for details.

## Writing custom models

The primary purpose of this repository is not to implement the Ising model
but to provide you with everything to create your own "model". A "model"
can be a "spin model" like the Ising model or anything else that has some
settings and produces data over time that you want to show in a webbrowser.
This could be a simulation but also something completely different like a
piece of hardware.

Try out the SpiMoSim creator to get a first impression what is possible in
SpiMoSim or to even write your whole model in the webbrowser. The
SpiMoSim creator is available at
<http://www.pascalgrafe.net/spimosim/spimosimCreator> and also part of the
main SpiMoSim repository if you want to run it locally. The SpiMoSim creator
is currently limited to models written in Javascript, but replacing a
Javascript model with a Python one is simple:

* Load the SimulationBackend module 'server' by adding/uncommenting
  the folling line in `ising/index.html`:
 
   `<script src="lib/modules/SimulationBackend/server.js"></script>`

* Set the simulation backend to 'server' and set the websocket URL
  by setting `modelConfig.simulation.backend` in `model-config.js` to:
 
   ```
   {
     type: "server",
     url: "ws://localhost:8090"
   }
   ```

* Write a custom model in python: Create a file with a name ending in
  `-model.py`. The file needs to define a Model inherited from
  `pyspimosim.base_model.BaseModel` that overwrites the methods
  
  - `async def step(self, vars_config, t)`
  
  or

  - `async def steps(self, vars_config, t, protocol, save_interval, next_send_time)`
  
  
  and
  
  - `async def change_settings(self, model_settings, restart=False)`.

  Also define the properties

  - `name: str`
  - `multi_step : bool`
  - `save_state_after_init : bool`
    
  
  A dataclass `ModelBackendSettings` is also needed for the model.
  It should inherit from `pyspimosim.base_model.ModelBackendSettings`
  is used to define model specific command line options.
  `pyspimosim.base_model.ModelBackendSettings` can also just be imported
  and left as is.

* Start the server. `python3 -m pyspimosim` has the optional argument
  `--model_backend_dir` to specify where you put your python model. This
  is not necessary if you make model an executable python script like
  the Ising model implementation. Use `--www_model_root` to specify the
  location of model specific files to be servered by the webserver.
