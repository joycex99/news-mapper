import React from 'react';
import ReactDOM from 'react-dom';

import WorldMap from './components/WorldMap';
import registerServiceWorker from './registerServiceWorker';


fetch("/countries_geo.json")
  .then(response => {
    if (response.status !== 200) {
      console.log("Problem fetching countries geojson: " + response.status);
      return;
    }
    response.json().then(countriesData => {
      ReactDOM.render(<WorldMap geoCountries={countriesData} />, document.getElementById('map'));
      console.log("Success loading country data");
    });
  });

// ReactDOM.render(<WorldMap />, document.getElementById('map'));
//registerServiceWorker();

// connect to mlab news database (assume populated after crawling)
// var mongoose = require('mongoose');
// var Schema = mongoose.Schema; 


// mongoose.connect()