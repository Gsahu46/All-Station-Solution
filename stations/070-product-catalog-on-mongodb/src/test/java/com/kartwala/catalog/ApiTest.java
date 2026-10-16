package com.kartwala.catalog;

import org.junit.jupiter.api.AfterEach;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.context.annotation.Import;
import org.springframework.data.mongodb.core.MongoTemplate;
import org.springframework.data.mongodb.core.query.Criteria;
import org.springframework.data.mongodb.core.query.Query;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.ResultActions;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;

/** Shared setup: the whole app on a real MongoDB with the six demo products. Test SKUs start with T- and are removed. */
@SpringBootTest
@AutoConfigureMockMvc
@Import(MongoTestConfig.class)
abstract class ApiTest {

    @Autowired
    MockMvc mvc;
    @Autowired
    MongoTemplate mongo;

    @AfterEach
    void removeTestProducts() {
        mongo.remove(new Query(Criteria.where("sku").regex("^T-")), "products");
    }

    ResultActions create(String body) throws Exception {
        return mvc.perform(post("/catalog/products").contentType(MediaType.APPLICATION_JSON).content(body));
    }
}
