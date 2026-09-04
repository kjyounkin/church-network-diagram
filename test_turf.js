const turf = require('@turf/turf');
const points = turf.randomPoint(200, {bbox: [0, 0, 10, 10]});
const clustered = turf.clustersKmeans(points, {numberOfCenters: 5});
let clusters = new Set();
turf.featureEach(clustered, function (f) {
  clusters.add(f.properties.cluster);
});
console.log("Number of clusters (options):", clusters.size);

const clustered2 = turf.clustersKmeans(points, {numberOfCenters: 10});
let clusters2 = new Set();
turf.featureEach(clustered2, function (f) {
  clusters2.add(f.properties.cluster);
});
console.log("Number of clusters (options=10):", clusters2.size);

const clustered3 = turf.clustersKmeans(points, {mutate: true});
let clusters3 = new Set();
turf.featureEach(clustered3, function (f) {
  clusters3.add(f.properties.cluster);
});
console.log("Number of clusters (no options):", clusters3.size);
