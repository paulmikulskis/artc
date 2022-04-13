
const data = [
  {
    title: 'The Awakening',
    author: 'Kate Chopin',
  },
  {
    title: 'City of Glass',
    author: 'Paul Auster',
  },
]

const influxStats = async () => {
  return {
    chatstats: {
      name: '',
      value: '',
    },
    programs: {
      name: '',
      arguments: []
    }
  }
}

// Resolvers define the technique for fetching the types defined in the
// schema. This resolver retrieves books from the "books" array above.
export const resolvers = {
  Query: {
    books: () => data,
    stats: () => await influxStats()
  },
}