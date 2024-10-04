require('dotenv').config();
const express = require('express');
const bodyParser = require('body-parser');
const { MongoClient } = require('mongodb');
const initTracer = require('jaeger-client').initTracer;
const cors = require('cors');

const app = express();
app.use(bodyParser.json());
app.use(cors());
app.set('view engine', 'ejs');

// Load environment variables
const SELF_PORT = process.env.SELF_PORT || 5003;
const MONGO_DB_HOST = process.env.MONGO_DB_HOST;
const MONGO_DB_PORT = process.env.MONGO_DB_PORT;
const MONGO_DB_USERNAME = process.env.MONGO_DB_USERNAME;
const MONGO_DB_PASSWORD = process.env.MONGO_DB_PASSWORD;
const JAEGER_AGENT_HOST = process.env.JAEGER_AGENT_HOST;
const JAEGER_AGENT_PORT = process.env.JAEGER_AGENT_PORT;

// Initialize Tracer
function initializeTracer() {
    const config = {
        serviceName: 'contacts',
        reporter: {
            agentHost: JAEGER_AGENT_HOST,
            agentPort: JAEGER_AGENT_PORT,
        },
        sampler: {
            type: 'const',
            param: 1,
        },
    };
    return initTracer(config);
}

const tracer = initializeTracer();

// DB connection
let client, contactsCollection, faqsCollection, convCollection, storageCollection;
let url = `mongodb://${MONGO_DB_USERNAME}:${MONGO_DB_PASSWORD}@${MONGO_DB_HOST}:${MONGO_DB_PORT}/`;

console.log('Attempting to connect to MongoDB...');
console.log(`MongoDB URL: ${url}`);// ****

MongoClient.connect(url, {
    useNewUrlParser: true,
    useUnifiedTopology: true,
    serverSelectionTimeoutMS: 5000, // 5 second timeout
    socketTimeoutMS: 45000, // 45 second timeout
})
    .then((connectedClient) => {
        client = connectedClient;
        const db = client.db('contact');
        contactsCollection = db.collection('contacts');
        faqsCollection = db.collection('faq');
        convCollection = db.collection('conversation');
        storageCollection = db.collection('storage');
        console.log("Connected to MongoDB successfully");
    })
    .catch((err) => {
        console.error("Failed to connect to MongoDB:", err);
    });

// ===================================================================================================================================================================================== //

app.get('/', (req, res) => {
    console.log('Received request for root route');
    res.send('Contact service is running');
});

// ===================================================================================================================================================================================== //

app.get('/testMongo', async (req, res) => {
    if (!client) {
        return res.status(500).json({ error: 'MongoDB client not initialized' });
    }
    try {
        await client.db().admin().ping();
        res.json({ message: 'MongoDB connection successful' });
    } catch (error) {
        res.status(500).json({ error: 'MongoDB connection failed', details: error.message });
    }
});

app.get('/getContacts', async (req, res) => {

    if (!contactsCollection) {
        console.error('Contacts collection is not initialized');
        return res.status(500).json({ error: 'Database not initialized' });
    }

    try {
        const contacts = await contactsCollection.find().toArray();

        const filteredContacts = contacts.map(contact => {
            const { _id, ...contactWithoutId } = contact;
            return contactWithoutId;
        });

        res.json(filteredContacts);
    } catch (error) {
        console.error('Error fetching contacts:', error);
        res.status(500).json({ error: 'Internal server error', details: error.message });
    }
});

app.get('/getFaqs', async (req, res) => {
    if (!faqsCollection) {
        console.error('FAQs collection is not initialized');
        res.status(500).send('Database not initialized');
        return;
    }

    try {
        const faqs = await faqsCollection.find().toArray();

        const filteredFaqs = faqs.map(faq => {
            const { _id, ...faqWithoutId } = faq;
            return faqWithoutId;
        });
        res.json(filteredFaqs);
    } catch (error) {
        console.error('Error fetching faqs:', error);
        res.status(500).json({ error: 'Internal server error', details: error.message });
    }
});

app.get('/getConvs', async (req, res) => {
    if (!contactsCollection) {
        console.error('Contacts collection is not initialized');
        res.status(500).send('Database not initialized');
        return;
    }

    try {
        let convs = await convCollection.find().toArray();

        const filteredConvs = convs.map(conv => {
            const { _id, ...convWithoutId } = conv;
            return convWithoutId;
        })
        res.json(filteredConvs);
    } catch (error) {
        console.error('Error fetching Conversations:', error);
        res.status(500).json({ error: 'Internal server error', details: error.message });
    }

})

app.get('/getClients', async (req, res) => {
    if (!storageCollection) {
        console.error('Storage collection is not initialized');
        res.status(500).send('Database not initialized');
        return;
    }

    try {
        let clients = await storageCollection.find().toArray();

        let filteredClients = clients.map(client => {
            const { _id, ...clientWithoutId } = client;
            return clientWithoutId;
        })

        res.json(filteredClients);
    } catch (error) {
        console.error('Error fetching Clients:', error);
        res.status(500).json({ error: 'Internal server error', details: error.message });
    }
})

app.get('/getClient/:id', async (req, res) => {
    if (!storageCollection) {
        console.error('Storage collection is not initialized');
        res.status(500).send('Database not initialized');
        return;
    }

    try {
        await storageCollection.findOne({ id: req.params.id }, (err, client) => {
            if (err) throw err;
            if (!client) res.status(404).send({});
            else res.json(client);
        });
    } catch (error) {
        console.error('Error fetching Client:', error);
        res.status(500).json({ error: 'Internal server error', details: error.message });
    }

});

// Error handling ==> middleware
app.use((err, req, res, next) => {
    console.error(err.stack);
    res.status(500).send('Something broke!');
});

// Start the server
app.listen(SELF_PORT, () => {
    console.log(`Server running on port ${SELF_PORT}`);
}).on('error', (err) => {
    console.error('Error starting server:', err);
});

// app.get('/', (req, res) => {
//     convCollection.find().toArray((err, convData) => {
//         if (err) {
//             return res.status(500).send(err);
//         }
//         res.render('index', {
//             conv_data: convData,
//             m_client: client,
//             MONGO_HOST: MONGO_DB_HOST,
//             MONGO_PORT: MONGO_DB_PORT,
//             MONGO_PASSWORD: MONGO_DB_PASSWORD,
//             MONGO_USERNAME: MONGO_DB_USERNAME,
//         });
//     });
// });

// // ===================================================================================================================================================================================== //

// app.post('/updateContacts', (req, res) => {
//     const span = tracer.startSpan('updateContacts');
//     const jsonData = req.body;
//     const region_id = jsonData.region_id;

//     contactsCollection.findOne({ region_id }, (err, existingContact) => {
//         if (err) {
//             return res.status(500).send(err);
//         }

//         if (existingContact) {
//             contactsCollection.updateOne({ region_id }, { $set: jsonData }, (err) => {
//                 if (err) {
//                     return res.status(500).send(err);
//                 }
//                 res.status(200).send({ message: 'Contact updated successfully' });
//                 span.finish();
//             })
//         } else {
//             contactsCollection.insertOne(jsonData, (err) => {
//                 if (err) {
//                     return res.status(500).send(err);
//                 }
//                 res.status(200).send({ message: 'Contact created successfully' });
//                 span.finish();
//             });
//         }
//     });
// });

// // ===================================================================================================================================================================================== //

// app.post('/updateFaqs', (req, res) => {
//     const span = tracer.startSpan('updateFaqs');
//     const jsonData = req.body;
//     const question_id = jsonData.question_id;

//     faqsCollection.findOne({ question_id }, (err, existingFaq) => {
//         if (err) {
//             return res.status(500).send(err);
//         }
//         if (existingFaq) {
//             faqsCollection.updateOne({ question_id }, { $set: jsonData }, (err) => {
//                 if (err) {
//                     return res.status(500).send(err);
//                 }
//                 res.status(200).send({ message: 'FAQ updated successfully' });
//                 span.finish();
//             })
//         } else {
//             faqsCollection.insertOne(jsonData, (err) => {
//                 if (err) {
//                     return res.status(500).send(err);
//                 }
//                 res.status(200).send({ message: 'FAQ created successfully' });
//                 span.finish();
//             });
//         }
//     })
// })

// // ===================================================================================================================================================================================== //


// app.post('/updateConvs', (req, res) => {
//     const span = tracer.startSpan('updateConvs');
//     const jsonData = req.body;
//     convCollection.insertOne(jsonData, (err) => {
//         if (err) {
//             return res.status(500).send(err);
//         }
//         res.status(200).send({ message: 'Conversation created successfully' });
//         span.finish();
//     })
// })

// // ===================================================================================================================================================================================== //

// app.post('/updateClient', (req, res) => {
//     const span = tracer.startSpan('updateClient');
//     const jsonData = req.body;
//     const client_id = jsonData.region_id;
//     storageCollection.findOne({ client_id }, (err, existingClient) => {
//         if (err) {
//             return res.status(500).send(err);
//         }
//         if (existingClient) {
//             storageCollection.updateOne({ client_id }, { $set: jsonData }, (err) => {
//                 if (err) {
//                     return res.status(500).send(err);
//                 }
//                 res.status(200).send({ message: 'Client updated successfully' });
//                 span.finish();
//             })
//         } else {
//             storageCollection.insertOne(jsonData, (err) => {
//                 if (err) {
//                     return res.status(500).send(err);
//                 }
//                 res.status(200).send({ message: 'Client created successfully' });
//                 span.finish();
//             })
//         }
//     })
// })



// // ===================================================================================================================================================================================== //

// app.listen(SELF_PORT, () => {
//     console.log(`Server running on port ${SELF_PORT}`);
// });