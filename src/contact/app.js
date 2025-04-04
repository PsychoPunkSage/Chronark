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
        serviceName: 'ms-contacts',
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

// app.use((req, res, next) => {
//     // const // span = tracer.startSpan(req.path, {
//     tags: { 'http.method': req.method, 'http.url': req.url },
// });
// // Attach the // span to the request object
// req.// span = // span;
//     res.on('finish', () => {
//         // span.setTag(opentracing.Tags.HTTP_STATUS_CODE, res.statusCode);
//         // span.finish();
//     });
// next();
// });

// =============================================================================================================== \\

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
    // req.// span.log({ event: 'handling / request' });
    console.log('Received request for root route');
    res.send('Contact service is running');
});

// ===================================================================================================================================================================================== //
// CVE-2022-24999

app.post('/dos-test', (req, res) => {
    // Just echo back the request size to demonstrate we received it
    // This will crash if payload is too large
    try {
        const payloadSize = JSON.stringify(req.body).length;
        console.log(`Received payload of size: ${payloadSize} bytes`);

        res.json({
            message: 'Request processed successfully',
            payloadSize: `${payloadSize} bytes`,
            payloadSizeMB: `${(payloadSize / (1024 * 1024)).toFixed(2)} MB`
        });
    } catch (error) {
        res.status(500).json({
            error: 'Server error processing request',
            message: error.message
        });
    }
});

// ===================================================================================================================================================================================== //

app.get('/testMongo', async (req, res) => {
    // const // span = tracer.startSpan('testMongo', { childOf: req.// span });

    if (!client) {
        // span.log({ event: 'error', message: 'MongoDB client not initialized' });
        // span.finish();
        return res.status(500).json({ error: 'MongoDB client not initialized' });
    }
    try {
        await client.db().admin().ping();
        // span.log({ event: 'MongoDB ping success' });
        res.json({ message: 'MongoDB connection successful' });
    } catch (error) {
        // span.log({ event: 'MongoDB connection failed', error: error.message });
        res.status(500).json({ error: 'MongoDB connection failed', details: error.message });
    }
});

// ===================================================================================================================================================================================== //

app.get('/getContacts', async (req, res) => {
    // const // span = tracer.startSpan('/contact/getContacts', { childOf: req.// span });

    if (!contactsCollection) {
        console.error('Contacts collection is not initialized');
        // span.log({ event: 'error', message: 'Database not initialized' });
        // span.finish();
        return res.status(500).json({ error: 'Database not initialized' });
    }

    try {
        const contacts = await contactsCollection.find().toArray();

        const filteredContacts = contacts.map(contact => {
            const { _id, ...contactWithoutId } = contact;
            return contactWithoutId;
        });

        // span.log({ event: 'contacts fetched', count: filteredContacts.length });

        res.json(filteredContacts);
    } catch (error) {
        console.error('Error fetching contacts:', error);
        // span.log({ event: 'error', error: error.message });
        res.status(500).json({ error: 'Internal server error', details: error.message });
    }
    // finally {
    // span.finish();
    // }
});

app.post('/updateContacts', async (req, res) => {
    // const // span = tracer.startSpan('/contact/updateContacts', { childOf: req.// span });

    if (!contactsCollection) {
        // span.log({ event: 'error', message: 'Database not initialized' });
        // span.finish();
        return res.status(500).json({ error: 'Database not initialized' });
    }

    const jsonData = req.body;
    const region_id = jsonData.region_id;

    if (!region_id) {
        console.error('region_id is missing from the request body');
        // span.log({ event: 'error', message: 'region_id missing' });
        // span.finish();
        return res.status(400).json({ error: 'region_id is required' });
    }

    try {
        const existingContact = await contactsCollection.findOne({ region_id: region_id });

        if (existingContact) {
            const result = await contactsCollection.updateOne({ region_id: region_id }, { $set: jsonData });
            if (result.modifiedCount === 1) {
                // span.log({ event: 'contact updated', region_id });
                res.status(200).json({ message: 'Contact updated successfully' });
            } else if (result.matchedCount === 1) {
                res.status(200).json({ message: 'No changes were made; contact was already up to date' });
            } else {
                res.status(404).json({ error: 'Contact not found or update failed' });
            }
        } else {
            const result = await contactsCollection.insertOne(jsonData);
            if (result.insertedId) {
                // span.log({ event: 'contact created', region_id });
                res.status(200).json({ message: 'Contact created successfully', id: result.insertedId });
            } else {
                res.status(500).json({ error: 'Failed to insert new contact' });
            }
        }
    } catch (error) {
        // span.log({ event: 'error', error: error.message });
        res.status(500).json({ error: 'Internal server error', details: error.message });
    }
    // finally {
    // span.finish();
    // }
});

// ===================================================================================================================================================================================== //

app.get('/getFaqs', async (req, res) => {
    // const // span = tracer.startSpan('/contact/getFaqs', { childOf: req.// span });

    if (!faqsCollection) {
        console.error('FAQs collection is not initialized');
        // span.log({ event: 'error', message: 'Database not initialized' });
        // span.finish();
        res.status(500).send('Database not initialized');
        return;
    }

    try {
        const faqs = await faqsCollection.find().toArray();

        const filteredFaqs = faqs.map(faq => {
            const { _id, ...faqWithoutId } = faq;
            return faqWithoutId;
        });

        // span.log({ event: 'faqs fetched', count: filteredFaqs.length });

        res.json(filteredFaqs);
    } catch (error) {
        console.error('Error fetching faqs:', error);
        // span.log({ event: 'error', error: error.message });
        res.status(500).json({ error: 'Internal server error', details: error.message });
    }
    // finally {
    // span.finish();
    // }
});

app.post('/updateFaqs', async (req, res) => {
    // const // span = tracer.startSpan('/contact/updateContacts', { childOf: req.// span });

    if (!faqsCollection) {
        console.error('Faqs collection is not initialized');
        // span.log({ event: 'error', message: 'Database not initialized' });
        // span.finish();
        return res.status(500).json({ error: 'Database not initialized' });
    }

    const jsonData = req.body;
    const question_id = jsonData.question_id;

    if (!question_id) {
        console.error('question_id is missing from the request body');
        // span.log({ event: 'error', message: 'question_id missing' });
        // span.finish();
        return res.status(400).json({ error: 'question_id is required' });
    }

    try {
        const existingFaq = await faqsCollection.findOne({ question_id: question_id });

        if (existingFaq) {
            const result = await faqsCollection.updateOne({ question_id: question_id }, { $set: jsonData });
            if (result.modifiedCount === 1) {
                // span.log({ event: 'Faq updated', region_id });
                res.status(200).json({ message: 'Faq updated successfully' });
            } else if (result.matchedCount === 1) {
                res.status(200).json({ message: 'No changes were made; Faq was already up to date' });
            } else {
                res.status(404).json({ error: 'Faq not found or update failed' });
            }
        } else {
            const result = await faqsCollection.insertOne(jsonData);
            if (result.insertedId) {
                // span.log({ event: 'faq created', region_id })
                res.status(200).json({ message: 'Faq created successfully', id: result.insertedId });
            } else {
                res.status(500).json({ error: 'Failed to insert new faq' });
            }
        }
    } catch (error) {
        console.error('Error in updateContacts:', error);
        // span.log({ event: 'error', error: error.message });
        res.status(500).json({ error: 'Internal server error', details: error.message });
    }
    // finally {
    // span.finish();
    // }
});

// ===================================================================================================================================================================================== //

app.get('/getConvs', async (req, res) => {
    // const // span = tracer.startSpan('/contact/getConvs', { childOf: req.// span });

    if (!contactsCollection) {
        console.error('Contacts collection is not initialized');
        // span.log({ event: 'error', message: 'Database not initialized' });
        // span.finish();
        res.status(500).send('Database not initialized');
        return;
    }

    try {
        let convs = await convCollection.find().toArray();

        const filteredConvs = convs.map(conv => {
            const { _id, ...convWithoutId } = conv;
            return convWithoutId;
        })

        // span.log({ event: 'Convs fetched', count: filteredConvs.length });

        res.json(filteredConvs);
    } catch (error) {
        console.error('Error fetching Conversations:', error);
        // span.log({ event: 'error', error: error.message });
        res.status(500).json({ error: 'Internal server error', details: error.message });
    }
    // finally {
    // span.finish();
    // }

})

app.post('/updateConvs', async (req, res) => {
    // const // span = tracer.startSpan('/contact/updateConvs', { childOf: req.// span });

    if (!convCollection) {
        console.error('Conv collection is not initialized');
        // span.log({ event: 'error', message: 'Database not initialized' });
        // span.finish();
        return res.status(500).json({ error: 'Database not initialized' });
    }

    const jsonData = req.body;
    try {
        const result = await convCollection.insertOne(jsonData);
        if (result.insertedId) {
            // span.log({ event: 'Conv created', id: result.insertedId })
            res.status(201).json({ message: 'Conversation saved successfully', id: result.insertedId });
        } else {
            res.status(500).json({ error: 'Failed to save new conversation. Please Retry!!' });
        }
    } catch (error) {
        console.error('Error in updateConvs:', error);
        // span.log({ event: 'error', error: error.message });
        res.status(500).json({ error: 'Internal server error', details: error.message });
    }
    // finally {
    // span.finish();
    // }
})

// ===================================================================================================================================================================================== //

app.get('/getClients', async (req, res) => {
    // const // span = tracer.startSpan('/contact/getClients', { childOf: req.// span });

    if (!storageCollection) {
        console.error('Storage collection is not initialized');
        // span.log({ event: 'error', message: 'Database not initialized' });
        // span.finish();
        res.status(500).send('Database not initialized');
        return;
    }

    try {
        let clients = await storageCollection.find().toArray();

        let filteredClients = clients.map(client => {
            const { _id, ...clientWithoutId } = client;
            return clientWithoutId;
        })

        // span.log({ event: 'Clients fetched', count: filteredClients.length });

        res.json(filteredClients);
    } catch (error) {
        console.error('Error fetching Clients:', error);
        // span.log({ event: 'error', error: error.message });
        res.status(500).json({ error: 'Internal server error', details: error.message });
    }
    // finally {
    // span.finish();
    // }
})

app.get('/getClient/:id', async (req, res) => {
    // const // span = tracer.startSpan('/contact/getClient/:id', { childOf: req.// span });

    if (!storageCollection) {
        console.error('Storage collection is not initialized');
        // span.log({ event: 'error', message: 'Database not initialized' });
        // span.finish();
        res.status(500).send('Database not initialized');
        return;
    }

    try {
        let client = await storageCollection.findOne({ id: req.params.id });
        if (client) {
            // span.log({ event: 'Conv created', id: req.params.id })
            res.json(client);
        } else {
            res.status(404).json({ error: 'Client not found' });
        }
    } catch (error) {
        console.error('Error fetching Clients:', error);
        // span.log({ event: 'error', error: error.message });
        res.status(500).json({ error: 'Internal server error', details: error.message });
    }
    // finally {
    // span.finish();
    // }

});

app.post('/updateClient', async (req, res) => {
    // const // span = tracer.startSpan('/contact/updateClient', { childOf: req.// span });

    if (!storageCollection) {
        console.error('Storage collection is not initialized');
        // span.log({ event: 'error', message: 'Database not initialized' });
        // span.finish();
        res.status(500).send('Database not initialized');
        return;
    }

    const jsonData = req.body;
    const client_id = jsonData.region_id;

    if (!client_id) {
        console.error('question_id is missing from the request body');
        // span.log({ event: 'error', message: 'client_id missing' });
        // span.finish();
        return res.status(400).json({ error: 'client_id is required' });
    }

    try {
        const existingStorage = await storageCollection.findOne({ client_id: client_id });

        if (existingStorage) {
            const result = await storageCollection.updateOne({ client_id: client_id }, { $set: jsonData });
            if (result.modifiedCount === 1) {
                // span.log({ event: 'Client updated', client_id })
                res.status(200).json({ message: 'Client updated successfully' });
            } else {
                res.status(404).json({ error: 'Client not found or not modified' });
            }
        } else {
            const result = await storageCollection.insertOne(jsonData);
            if (result.insertedId) {
                // span.log({ event: 'Client created', client_id })
                res.status(201).json({ message: 'Client created successfully', id: result.insertedId });
            } else {
                res.status(500).json({ error: 'Failed to insert new client' });
            }
        }
    } catch (error) {
        console.error('Error in updateClient:', error);
        // span.log({ event: 'error', error: error.message });
        res.status(500).json({ error: 'Internal server error', details: error.message });
    }
    // finally {
    // span.finish();
    // }
});

// ===================================================================================================================================================================================== //

app.post('/clearContacts', async (req, res) => {
    // const // span = tracer.startSpan('/contact/clearContacts', { childOf: req.// span });

    if (!contactsCollection) {
        console.error('Contacts collection is not initialized');
        // span.log({ event: 'error', message: 'Database not initialized' });
        // span.finish();
        res.status(500).send('Database not initialized');
        return;
    }

    try {
        let result = await contactsCollection.deleteMany({});
        if (result.deletedCount > 0) {  // Check the number of deleted documents
            // span.log({ event: 'contact created', count: result.deletedCount });
            res.status(200).json({ message: 'Contacts deleted successfully', deletedCount: result.deletedCount });
        } else {
            res.status(404).json({ error: 'No contacts found to delete' });
        }
    } catch (error) {
        console.error('Error in clearContacts:', error);
        res.status(500).json({ error: 'Internal server error', details: error.message });
    }
})

// ===================================================================================================================================================================================== //

// Error handling ==> middleware
app.use((err, req, res, next) => {
    // if (req.// span) {
    //     req.// span.log({ event: 'error', message: err.message });
    //     req.// span.finish();
    // }
    console.error(err.stack);
    res.status(500).send('Something broke!');
});

// Start the server
app.listen(SELF_PORT, () => {
    console.log(`Server running on port ${SELF_PORT}`);
}).on('error', (err) => {
    console.error('Error starting server:', err);
});