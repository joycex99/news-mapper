import React, { Component } from 'react'
import axios from 'axios'
import { Map, TileLayer, Marker, Popup, GeoJSON } from 'react-leaflet'


// Example:
// https://www.azavea.com/blog/2016/12/05/getting-started-with-react-and-leaflet/

/*
state:
countryArticles = {count: ____, articles: [{id: 123, content: ...}, ...]}
*/

class WorldMap extends Component {
  constructor(props) {
    super(props);
    this.state = {
      center: [30.0, 0.0],
      zoomSnap: 0.25,
      zoom: 2.25,
      geoCountries: this.props.geoCountries,
      countryArticles: {}
    };

    this.highlightFeature = this.highlightFeature.bind(this);
    this.resetHighlight = this.resetHighlight.bind(this);
  }

  componentDidMount() {
    axios.get("/api/data")
      .then(result => {
        result.data.forEach(article => {
          var news = {"title": article.title,
                      "description": article.description,
                      "locations": article.locations};
          article.locations.forEach(location => {
            var currentCount, currentArticles;
            if (!this.state.countryArticles[location]) {
              currentCount = 0;
              currentArticles = [];
            } else {
              currentCount = this.state.countryArticles[location]["count"] || 0;
              currentArticles = this.state.countryArticles[location]["articles"]; 
            }
            this.setState({
              countryArticles: {
                ...this.state.countryArticles,
                [location]: {
                  count: currentCount+1,
                  articles: [...currentArticles, news]
                }
              }
              // countryArticles[location].count: currentCount+1,
              // countryArticles[location].articles: [...currentArticles, news]
            });
          });
        });
        console.log("Success fetching from /api/data: " + JSON.stringify(this.state.countryArticles));
      })
      .catch(error => {
        console.log("Problem loading API data endpoint: " + error);
      });
  }
  
  styleCountries(feature) {
    return {
      weight: 1,
      opacity: 1,
      color: 'white',
      dashArray: '',
      fillOpacity: 0.7,
      fillColor: "rgb(" + Math.floor(Math.random() * 255) + ",0,0)"
    }
  }

  highlightFeature(e) {
    //console.log("highlighting feature");
    var layer = e.target;
    layer.setStyle({
      weight: 1,
      color: '#666',
      dashArray: '',
      fillOpacity: 0.7
    });
    layer.bringToFront();
  }

  resetHighlight(e) {
    //console.log("resetting feature");
    this.refs.geojson.leafletElement.resetStyle(e.target); // https://www.codesd.com/item/react-leaflet-how-to-resetstyle.html
  }

  onEachFeature(feature, layer) {
    layer.on({
      mouseover: this.highlightFeature,
      mouseout: this.resetHighlight
    });
    //layer.bindPopup(feature.properties.name);
  }

  // Thunderforest map:
  // apikey="20dd883d1ed6449ca94c94fb4d843863"
  // url="https://{s}.tile.thunderforest.com/transport/{z}/{x}/{y}.png?apikey={apikey}"

  render() {
    return (
      <div>
        <Map center={this.state.center} zoomSnap={this.state.zoomSnap} zoom={this.state.zoom}>
          <TileLayer
            url="https://{s}.tile.openstreetmap.de/tiles/osmde/{z}/{x}/{y}.png"
            maxZoom="5"
          />
          <GeoJSON
            data={this.state.geoCountries}
            style={this.styleCountries}
            onEachFeature={this.onEachFeature.bind(this)}
            ref="geojson"
          />
          <Marker position={this.state.center}>
            <Popup>
              <span>
                Popup! <br /> One sample article: {JSON.stringify(this.state.countryArticles.Myanmar)}
              </span>
            </Popup>
          </Marker>
        </Map>
      </div>
    )
  }
}


export default WorldMap;