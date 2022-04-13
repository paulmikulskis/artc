import { ApolloServer, gql } from 'apollo-server'
import { loadSchema } from '@graphql-tools/load'
import { GraphQLFileLoader } from '@graphql-tools/graphql-file-loader'
import { resolvers } from './resolvers.js'

// load from a single schema file
const typeDefs = await loadSchema('graphql/*.graphql', {
  loaders: [new GraphQLFileLoader()]
})

// The ApolloServer constructor requires two parameters: your schema
// definition and your set of resolvers.
const server = new ApolloServer({ typeDefs, resolvers });

// The `listen` method launches a web server.
server.listen().then(({ url }) => {
  console.log(`🚀  Server ready at ${url}`)
})