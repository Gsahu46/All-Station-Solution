-- A GIN index holds, for every word, the list of dishes containing it: a search reads only those lists.
CREATE INDEX dishes_search ON dishes USING GIN (search);
CREATE INDEX dishes_city ON dishes (city);
ANALYZE dishes;
