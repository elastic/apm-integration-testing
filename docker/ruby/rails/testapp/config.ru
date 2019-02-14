# This file is used by Rack-based servers to start the application.

require_relative 'config/environment'

ElasticAPM.add_filter(:healthcheck) do |payload|
  payload[:transactions]&.reject! do |t|
    t[:name] == 'ApplicationController#healthcheck'
  end
  payload
end

run Rails.application
