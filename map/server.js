const express = require("express");
var mongoose = require("mongoose");
var Article = require("./articleSchema")

const app = express();
const port = process.env.PORT || 3001;


// mlab mongo db config
var dbuser = "joycexu"
var dbpass = "news"
mongoose.connect("mongodb://" + dbuser + ":" + dbpass + "@ds143907.mlab.com:43907/world-news");


app.get("/api/data", (req, res) => {
  Article.find().lean().exec((err, items) => {
    res.json(items);
    // items.forEach(item => {
    //   if (item == null) {
    //     return;
    //   }
    // });
  });
});


app.get("/api/test", (req, res) => {
  //res.json({ "test": "Hello World" });
  Article.findOne({}).then(result => {
    var art = {"title": result.title, "description": result.description};
    res.json(art);
  });
});



app.listen(port, () => console.log(`Listening on port ${port}`));