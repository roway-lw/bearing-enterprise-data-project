/** 数据库配置 API */
import client from './client'

export function testConnection(data: {
  host: string
  port: number
  user: string
  password: string
  database: string
}): Promise<{ connected: boolean; tables: string[]; database: string; message: string }> {
  return client.post('/api/db/test-connection', data)
}

export function initDatabase(data: {
  host: string
  port: number
  user: string
  password: string
  database: string
  tag_table?: string
  fact_table?: string
}): Promise<any> {
  return client.post('/api/db/init', data)
}

export function listTables(data: {
  host: string
  port: number
  user: string
  password: string
  database: string
}): Promise<{ tables: string[] }> {
  return client.post('/api/db/tables', data)
}

export function listColumns(data: {
  table_name: string
  name_column: string
}): Promise<{ columns: string[] }> {
  return client.post('/api/db/columns', data)
}

export function queryNames(data: {
  table_name: string
  name_column: string
  where_clause?: string
  limit?: number
}): Promise<{ names: string[]; count: number }> {
  return client.post('/api/db/query-names', data)
}

export function getDbConfig(): Promise<any> {
  return client.get('/api/db/config')
}
